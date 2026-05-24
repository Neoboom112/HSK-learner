from __future__ import annotations

from app.handlers.admin import router as admin_router
from app.handlers.dictionary import router as dictionary_router
from app.handlers.errors import router as errors_router
from app.handlers.learning import router as learning_router
from app.handlers.menu import router as menu_router
from app.handlers.progress import router as progress_router
from app.handlers.start import router as start_router


def get_routers():
    return [
        start_router,
        menu_router,
        dictionary_router,
        learning_router,
        progress_router,
        admin_router,
        errors_router,
    ]
