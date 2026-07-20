from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import Settings
from app.handlers import register_routers
from app.keyboards.inline import versioned_mini_app_url


def create_bot_and_dispatcher(settings: Settings) -> tuple[Bot, Dispatcher]:
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    register_routers(dp)
    return bot, dp


async def setup_bot_commands(bot: Bot, mini_app_url: str | None = None) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="app", description="Открыть MedAlarm"),
        ]
    )
    if mini_app_url and mini_app_url.startswith("https://"):
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Открыть MedAlarm",
                web_app=WebAppInfo(url=versioned_mini_app_url(mini_app_url)),
            )
        )
