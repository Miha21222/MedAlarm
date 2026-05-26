from aiogram import Dispatcher

from app.handlers.callbacks import router as callbacks_router
from app.handlers.history import router as history_router
from app.handlers.medicines import router as medicines_router
from app.handlers.settings import router as settings_router
from app.handlers.start import router as start_router


def register_routers(dp: Dispatcher) -> None:
    dp.include_router(start_router)
    dp.include_router(medicines_router)
    dp.include_router(history_router)
    dp.include_router(settings_router)
    dp.include_router(callbacks_router)
