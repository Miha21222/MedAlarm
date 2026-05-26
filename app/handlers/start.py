from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.config import load_settings
from app.database.session import session_scope
from app.services.user_service import UserService

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    if message.from_user is None:
        return
    settings = load_settings()
    async with session_scope() as session:
        await UserService.register_or_update_user(
            session=session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            default_timezone=settings.default_timezone,
        )
    await message.answer(
        "Привет! Я MedAlarm.\n\n"
        "Я напоминаю о приёме лекарств по твоему расписанию.\n"
        "Я не даю медицинских рекомендаций и не меняю схему лечения.\n\n"
        "Команды:\n"
        "/add_medicine - добавить лекарство\n"
        "/my_medicines - мои лекарства\n"
        "/today - план на сегодня\n"
        "/history - история приёмов\n"
        "/settings - настройки",
    )

