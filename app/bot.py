from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import Settings
from app.handlers import register_routers


def create_bot_and_dispatcher(settings: Settings) -> tuple[Bot, Dispatcher]:
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    register_routers(dp)
    return bot, dp


async def setup_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="menu", description="Открыть главное меню"),
        ]
    )
