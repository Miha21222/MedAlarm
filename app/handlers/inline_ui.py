from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.config import load_settings
from app.database.session import session_scope
from app.keyboards.inline import open_mini_app_keyboard
from app.services.user_service import UserService

router = Router()


async def _register_user(message: Message) -> None:
    user = message.from_user
    if user is None:
        return
    settings = load_settings()
    async with session_scope() as session:
        await UserService.register_or_update_user(
            session=session,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            default_timezone=settings.default_timezone,
        )


async def _delete_message_safe(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


@router.message(Command("start"))
@router.message(Command("app"))
async def start(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await _register_user(message)
    await state.clear()
    await message.answer(
        "Привет! Я MedAlarm.\n\n"
        "Я напоминаю о приёме лекарств по вашему расписанию.\n"
        "Я не даю медицинских рекомендаций и не изменяю схему лечения.",
        reply_markup=open_mini_app_keyboard(),
    )
    await _delete_message_safe(message)
