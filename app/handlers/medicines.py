from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from app.database.session import session_scope
from app.keyboards.inline import medicine_confirm_keyboard, medicine_manage_keyboard
from app.keyboards.reply import frequency_keyboard, repeat_keyboard
from app.services.intake_service import IntakeService
from app.services.medicine_service import MedicineService
from app.services.schedule_service import ScheduleService
from app.services.user_service import UserService
from app.states.medicine_states import AddMedicineStates
from app.utils.datetime_utils import (
    format_days,
    normalize_time_string,
    now_in_timezone,
    parse_days_input,
)

router = Router()


@router.message(Command("add_medicine"))
async def cmd_add_medicine(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(AddMedicineStates.name)
    await message.answer("Введите название лекарства:")


@router.message(AddMedicineStates.name)
async def add_medicine_name(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Название не может быть пустым.")
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(AddMedicineStates.dosage)
    await message.answer("Введите дозировку (например: 1 таблетка, 5 мл):")


@router.message(AddMedicineStates.dosage)
async def add_medicine_dosage(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Дозировка не может быть пустой.")
        return
    await state.update_data(dosage_text=message.text.strip())
    await state.set_state(AddMedicineStates.time)
    await message.answer("Введите время приёма в формате ЧЧ:ММ (например 21:00):")


@router.message(AddMedicineStates.time)
async def add_medicine_time(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Время не может быть пустым.")
        return
    try:
        normalized_time = normalize_time_string(message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await state.update_data(time=normalized_time)
    await state.set_state(AddMedicineStates.frequency)
    await message.answer("Как часто принимать?", reply_markup=frequency_keyboard())


@router.message(AddMedicineStates.frequency)
async def add_medicine_frequency(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Выберите вариант частоты.")
        return
    value = message.text.strip().lower()
    if value == "каждый день":
        await state.update_data(days_of_week="*")
        await state.set_state(AddMedicineStates.repeat)
        await message.answer("Повторять напоминания до подтверждения?", reply_markup=repeat_keyboard())
        return
    if value == "конкретные дни недели":
        await state.set_state(AddMedicineStates.days)
        await message.answer(
            "Введите дни через запятую: 1-7 (1=Пн, 7=Вс) или пн,ср,пт",
            reply_markup=ReplyKeyboardRemove(),
        )
        return
    await message.answer("Выберите: 'Каждый день' или 'Конкретные дни недели'.")


@router.message(AddMedicineStates.days)
async def add_medicine_days(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Введите дни недели.")
        return
    try:
        days = parse_days_input(message.text)
    except ValueError as exc:
        await message.answer(str(exc))
        return
    await state.update_data(days_of_week=",".join(str(day) for day in days))
    await state.set_state(AddMedicineStates.repeat)
    await message.answer("Повторять напоминания до подтверждения?", reply_markup=repeat_keyboard())


@router.message(AddMedicineStates.repeat)
async def add_medicine_repeat(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("Выберите Да или Нет.")
        return
    value = message.text.strip().lower()
    if value not in {"да", "нет"}:
        await message.answer("Введите Да или Нет.")
        return
    await state.update_data(remind_until_confirmed=value == "да")
    await state.set_state(AddMedicineStates.comment)
    await message.answer(
        "Введите комментарий (необязательно). Если не нужен, отправьте '-'",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(AddMedicineStates.comment)
async def add_medicine_comment(message: Message, state: FSMContext) -> None:
    comment = (message.text or "").strip()
    await state.update_data(comment=None if comment == "-" else comment)
    data = await state.get_data()
    summary = (
        f"Лекарство: {data['name']}\n"
        f"Дозировка: {data['dosage_text']}\n"
        f"Время: {data['time']}\n"
        f"Частота: {format_days(data['days_of_week'])}\n"
        f"Повторы: {'включены' if data['remind_until_confirmed'] else 'выключены'}\n"
        f"Комментарий: {data['comment'] or '—'}"
    )
    await state.set_state(AddMedicineStates.confirm)
    await message.answer(summary, reply_markup=medicine_confirm_keyboard())


@router.message(Command("my_medicines"))
async def cmd_my_medicines(message: Message) -> None:
    if message.from_user is None:
        return
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            await message.answer("Сначала запустите /start.")
            return
        medicines = await MedicineService.list_all_user_medicines(session, user.id)
    if not medicines:
        await message.answer("Список пуст. Добавьте первое лекарство командой /add_medicine.")
        return
    for medicine in medicines:
        schedule = medicine.schedules[0] if medicine.schedules else None
        schedule_text = (
            f"{schedule.time}, {format_days(schedule.days_of_week)}" if schedule else "расписание не задано"
        )
        status = "активно" if medicine.is_active else "неактивно"
        await message.answer(
            f"ID {medicine.id} | {medicine.name}\n"
            f"Дозировка: {medicine.dosage_text}\n"
            f"Расписание: {schedule_text}\n"
            f"Статус: {status}",
            reply_markup=medicine_manage_keyboard(medicine.id, medicine.is_active),
        )


@router.message(Command("today"))
async def cmd_today(message: Message) -> None:
    if message.from_user is None:
        return
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, message.from_user.id)
        if user is None:
            await message.answer("Сначала запустите /start.")
            return
        local_date = now_in_timezone(user.timezone).date()
        due_medicines = await ScheduleService.get_user_today_medicines(session, user.id, local_date)
        today_status = await IntakeService.today_status_by_medicine(
            session=session,
            user_id=user.id,
            local_date=local_date,
            timezone_name=user.timezone,
        )
    if not due_medicines:
        await message.answer("На сегодня активных приёмов нет.")
        return
    lines = ["Сегодня нужно принять:"]
    for medicine in due_medicines:
        schedule = medicine.schedules[0] if medicine.schedules else None
        taken_mark = " ✅" if today_status.get(medicine.id) == "taken" else ""
        lines.append(
            f"- {medicine.name} ({medicine.dosage_text}) в {schedule.time if schedule else '??:??'}{taken_mark}"
        )
    await message.answer("\n".join(lines))

