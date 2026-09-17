from __future__ import annotations

from datetime import datetime, timezone
from random import choice, shuffle

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.callbacks import LearningCallback
from app.database.models import Card
from app.keyboards.common import main_menu_keyboard
from app.keyboards.learning import after_answer_keyboard, rating_keyboard
from app.models.enums import LearningMode
from app.repositories.cards import CardRepository
from app.repositories.sessions import SessionRepository
from app.repositories.users import UserRepository
from app.services.learning_service import LearningService
from app.states import LearningState
from app.utils.text import compact_dt
from app.handlers.common import answer_accepted, format_card

router = Router(name=__name__)


class NotMenuText(BaseFilter):
    """Let commands and menu buttons reach the menu router.

    While a card waits for a typed answer every plain text is graded, which must
    not swallow "/progress" or a tap on the persistent menu keyboard.
    """

    async def __call__(self, message: Message, t=None) -> bool:
        text = (message.text or "").strip()
        if not text or text.startswith("/"):
            return False
        if t is None:
            return True
        return text not in {
            t("menu_select_dictionary"),
            t("menu_start_learning"),
            t("menu_progress"),
            t("menu_help"),
        }


def _normalize_mode(mode: str) -> LearningMode:
    try:
        return LearningMode(mode)
    except ValueError:
        return LearningMode.FLASHCARD


def _multiple_choice_keyboard(t, card: Card, options: list[str], mode: LearningMode) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for option in options:
        grade = 5 if option == (card.translation or card.hanzi) else 2
        builder.button(
            text=option[:36],
            callback_data=LearningCallback(action="grade", mode=mode.value, card_id=card.id, grade=grade).pack(),
        )
    builder.adjust(1)
    return builder.as_markup()


@router.callback_query(LearningCallback.filter(F.action == "mode"))
async def choose_mode(callback: CallbackQuery, callback_data: LearningCallback, session, state: FSMContext, t, locale: str) -> None:
    user_repo = UserRepository(session)
    user = await user_repo.get_or_create(
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        full_name=callback.from_user.full_name,
        language=locale,
    )
    service = LearningService(session)
    mode = _normalize_mode(callback_data.mode)
    session_row = await SessionRepository(session).start(user.id, mode.value, metadata={"source": "telegram"})
    card = await service.next_card(user.id, mode, dictionary_id=user.active_dictionary_id)
    if card is None:
        await callback.message.edit_text(t("learn_no_cards"))
        await callback.answer()
        return

    await state.set_state(LearningState.answering)
    await state.update_data(
        mode=mode.value,
        session_id=session_row.id,
        card_id=card.id,
        seen=0,
        correct=0,
        wrong=0,
        started_at=datetime.now(timezone.utc).isoformat(),
    )
    await callback.message.edit_text(t("learn_mode_started", mode=t(f"mode_{mode.value}")))
    # user.id (the internal one) - the telegram id would make the card pool empty.
    await _send_card(callback.message.answer, card, mode, t, user.id, session, state)
    await callback.answer()


async def _send_card(answer_func, card: Card, mode: LearningMode, t, user_id: int, session, state: FSMContext) -> None:
    if mode == LearningMode.MULTIPLE_CHOICE:
        repo = CardRepository(session)
        pool = await repo.get_random_cards(user_id, limit=30, dictionary_id=card.dictionary_id)
        correct = card.translation or card.hanzi
        options = [correct]
        for item in pool:
            candidate = item.translation or item.hanzi
            if item.id != card.id and candidate and candidate not in options:
                options.append(candidate)
            if len(options) >= 4:
                break

        if len(options) < 2:
            # Not enough different translations in the deck to build a quiz.
            await answer_func(
                f"{t('learn_quiz_unavailable')}\n\n{format_card(card, include_translation=False)}",
                reply_markup=rating_keyboard(t, card.id, mode.value),
            )
            return

        shuffle(options)
        text = f"{t('learn_question')}\n\n{card.hanzi}\n{card.pinyin or ''}".strip()
        await answer_func(
            text,
            reply_markup=_multiple_choice_keyboard(t, card, options, mode),
        )
        await state.update_data(current_prompt=text, correct_answer=correct)
        return

    if mode == LearningMode.TYPING:
        await answer_func(
            f"{t('learn_type_answer')}\n\n{format_card(card, include_translation=False)}",
        )
        await state.update_data(expected=card.translation or card.hanzi)
        return

    if mode == LearningMode.LISTENING and card.audio:
        await answer_func(
            f"{t('learn_listen')}\n\n{format_card(card, include_translation=False)}",
        )
        await state.update_data(expected=card.translation or card.hanzi)
        return

    await answer_func(
        f"{t('learn_flashcard')}\n\n{format_card(card, include_translation=False)}",
        reply_markup=rating_keyboard(t, card.id, mode.value),
    )


@router.callback_query(LearningCallback.filter(F.action == "grade"))
async def review_card(callback: CallbackQuery, callback_data: LearningCallback, session, state: FSMContext, t) -> None:
    data = await state.get_data()
    mode = _normalize_mode(data.get("mode", "flashcard"))
    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("need_start"), show_alert=True)
        return
    service = LearningService(session)
    try:
        card, is_correct = await service.answer(user.id, callback_data.card_id, callback_data.grade, mode)
    except ValueError:
        # Stale button (for example after the progress was reset) or a crafted id.
        await callback.answer(t("learn_card_not_found"), show_alert=True)
        return
    data["seen"] = int(data.get("seen", 0)) + 1
    if is_correct:
        data["correct"] = int(data.get("correct", 0)) + 1
    else:
        data["wrong"] = int(data.get("wrong", 0)) + 1
    await state.update_data(**data)
    verdict = t("answer_correct") if is_correct else t("answer_wrong")
    text = (
        f"{t('answer_recorded')} — <b>{verdict}</b>\n\n"
        f"{t('learn_answer')}\n{format_card(card)}\n\n"
        f"{t('next_due')}: {compact_dt(card.due_at)}"
    )
    await callback.message.edit_text(text, reply_markup=after_answer_keyboard(t))
    await callback.answer()


@router.callback_query(LearningCallback.filter(F.action == "skip"))
async def skip_card(callback: CallbackQuery, callback_data: LearningCallback, session, state: FSMContext, t, locale: str) -> None:
    data = await state.get_data()
    mode = _normalize_mode(data.get("mode", "flashcard"))
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("need_start"), show_alert=True)
        return

    # Skipped cards leave the session queue and their message is removed, so the
    # chat does not fill up with "skipped" notes.
    skipped = [int(card_id) for card_id in data.get("skipped_ids", [])]
    if callback_data.card_id and callback_data.card_id not in skipped:
        skipped.append(callback_data.card_id)
    await state.update_data(skipped_ids=skipped)

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    card = await LearningService(session).next_card(
        user.id, mode, exclude=skipped, dictionary_id=user.active_dictionary_id
    )
    if card is None:
        await callback.message.answer(
            t("learn_skipped_all") if skipped else t("learn_no_cards"),
            reply_markup=main_menu_keyboard(t),
        )
        await state.clear()
        await callback.answer()
        return

    await state.update_data(card_id=card.id)
    await _send_card(callback.message.answer, card, mode, t, user.id, session, state)
    await callback.answer()


@router.message(LearningState.answering, F.text, NotMenuText())
async def typing_answer(message: Message, session, state: FSMContext, t) -> None:
    data = await state.get_data()
    expected = data.get("expected")
    card_id = data.get("card_id")
    mode = _normalize_mode(data.get("mode", "typing"))
    if not expected or not card_id:
        await message.answer(t("learn_no_active_card"))
        return

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(message.from_user.id)
    if user is None:
        await message.answer(t("need_start"))
        return

    card_repo = CardRepository(session)
    card = await card_repo.get_by_id(int(card_id), user.id)
    if card is None:
        await message.answer(t("learn_no_active_card"))
        return

    accepted = answer_accepted(message.text, card)
    if not accepted:
        # The same word may live in another deck of this user with a translation
        # in another language, so those variants count as correct too.
        siblings = await card_repo.get_by_hanzi(user.id, card.hanzi)
        accepted = any(answer_accepted(message.text, other) for other in siblings)
    grade = 5 if accepted else 2
    service = LearningService(session)
    updated_card, _ = await service.answer(user.id, card.id, grade, mode)
    data["seen"] = int(data.get("seen", 0)) + 1
    if accepted:
        data["correct"] = int(data.get("correct", 0)) + 1
    else:
        data["wrong"] = int(data.get("wrong", 0)) + 1
    await state.update_data(**data)
    verdict = t("answer_correct") if accepted else t("answer_wrong")
    await message.answer(
        f"{t('answer_recorded')} — <b>{verdict}</b>\n\n"
        f"{t('learn_answer')}\n{format_card(updated_card)}",
        reply_markup=after_answer_keyboard(t),
    )


@router.callback_query(LearningCallback.filter(F.action == "next"))
async def next_card(callback: CallbackQuery, session, state: FSMContext, t, locale: str) -> None:
    data = await state.get_data()
    mode = _normalize_mode(data.get("mode", "flashcard"))
    user = await UserRepository(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await callback.answer(t("need_start"), show_alert=True)
        return
    card = await LearningService(session).next_card(
        user.id, mode, exclude=data.get("skipped_ids"), dictionary_id=user.active_dictionary_id
    )
    if card is None:
        await callback.message.edit_text(t("learn_no_cards"))
        await callback.message.answer(t("back_to_menu"), reply_markup=main_menu_keyboard(t))
        await state.clear()
        await callback.answer()
        return
    await state.update_data(card_id=card.id)
    await _send_card(callback.message.answer, card, mode, t, user.id, session, state)
    await callback.answer()


@router.callback_query(LearningCallback.filter(F.action == "stop"))
async def stop_learning(callback: CallbackQuery, session, state: FSMContext, t) -> None:
    data = await state.get_data()
    session_id = data.get("session_id")
    if session_id:
        await SessionRepository(session).finish(
            int(session_id),
            cards_seen=int(data.get("seen", 0)),
            correct_answers=int(data.get("correct", 0)),
            wrong_answers=int(data.get("wrong", 0)),
        )
    await state.clear()
    await callback.message.edit_text(t("learn_stopped"))
    await callback.message.answer(t("back_to_menu"), reply_markup=main_menu_keyboard(t))
    await callback.answer()
