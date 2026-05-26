from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app.database.session import session_scope
from app.keyboards.inline import settings_keyboard
from app.keyboards.reply import settings_repeat_keyboard
from app.scheduler.setup import get_scheduler
from app.services.user_service import UserService
from app.states.settings_states import SettingsStates
from app.utils.datetime_utils import validate_timezone

router = Router()


@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    if message.from_user is None:
        return
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            await message.answer("Сначала запустите /start.")
            return
    await message.answer(
        f"Текущие настройки:\n"
        f"TZ: {user.timezone}\n"
        f"Snooze: {user.default_snooze_minutes} мин\n"
        f"Повторы: {'on' if user.remind_until_confirmed else 'off'}",
        reply_markup=settings_keyboard(),
    )


@router.callback_query(F.data == "settings_tz")
async def settings_tz(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.timezone)
    await callback.message.answer("Введите IANA timezone, например Europe/Kyiv:")
    await callback.answer()


@router.callback_query(F.data == "settings_snooze")
async def settings_snooze(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.snooze)
    await callback.message.answer("Введите snooze в минутах (1-180):")
    await callback.answer()


@router.callback_query(F.data == "settings_repeat")
async def settings_repeat(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.repeats)
    await callback.message.answer("Введите режим повторов: on / off", reply_markup=settings_repeat_keyboard())
    await callback.answer()


@router.message(SettingsStates.timezone)
async def set_timezone(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not message.text:
        return
    timezone_name = message.text.strip()
    if not validate_timezone(timezone_name):
        await message.answer("Некорректный timezone. Пример: Europe/Kyiv.")
        return
    async with session_scope() as session:
        user = await UserService.update_timezone(session, message.from_user.id, timezone_name)
    await state.clear()
    await message.answer(f"Часовой пояс обновлён: {timezone_name}", reply_markup=ReplyKeyboardRemove())
    if user:
        scheduler = get_scheduler()
        if scheduler:
            await scheduler.reload_jobs()


@router.message(SettingsStates.snooze)
async def set_snooze(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not message.text:
        return
    if not message.text.isdigit():
        await message.answer("Введите целое число 1-180.")
        return
    minutes = int(message.text)
    if minutes < 1 or minutes > 180:
        await message.answer("Введите значение в диапазоне 1-180.")
        return
    async with session_scope() as session:
        await UserService.update_snooze_minutes(session, message.from_user.id, minutes)
    await state.clear()
    await message.answer(f"Snooze по умолчанию обновлён: {minutes} мин.", reply_markup=ReplyKeyboardRemove())


@router.message(SettingsStates.repeats)
async def set_repeats(message: Message, state: FSMContext) -> None:
    if message.from_user is None or not message.text:
        return
    value = message.text.strip().lower()
    if value not in {"on", "off"}:
        await message.answer("Введите on или off.")
        return
    remind = value == "on"
    async with session_scope() as session:
        await UserService.update_repeat_mode(session, message.from_user.id, remind)
    await state.clear()
    await message.answer(f"Повторы {'включены' if remind else 'выключены'}.", reply_markup=ReplyKeyboardRemove())

