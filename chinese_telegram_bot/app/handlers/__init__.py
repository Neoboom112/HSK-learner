from __future__ import annotations

from app.handlers.admin import router as admin_router
from app.handlers.dictionary import router as dictionary_router
from app.handlers.errors import router as errors_router
from app.handlers.learning import router as learning_router
from app.handlers.menu import router as menu_router
from app.handlers.progress import router as progress_router
from app.handlers.start import router as start_router


def get_routers():
    """Routers in evaluation order.

    The menu router answers every plain text message, so it has to come after
    the stateful routers (:mod:`app.handlers.dictionary` waits for an uploaded
    file, :mod:`app.handlers.learning` waits for a typed answer) and after the
    command router of :mod:`app.handlers.admin`.  Otherwise the first matching
    handler wins and those flows never see the message.
    """
    return [
        start_router,
        dictionary_router,
        learning_router,
        admin_router,
        menu_router,
        progress_router,
        errors_router,
    ]
