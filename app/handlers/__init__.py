from aiogram import Dispatcher

from app.handlers.callbacks import router as callbacks_router
from app.handlers.inline_ui import router as inline_ui_router


def register_routers(dp: Dispatcher) -> None:
    dp.include_router(inline_ui_router)
    dp.include_router(callbacks_router)
