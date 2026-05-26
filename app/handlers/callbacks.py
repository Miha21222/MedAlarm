from __future__ import annotations

from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.database.session import session_scope
from app.keyboards.inline import medicine_delete_confirm_keyboard
from app.scheduler.setup import get_scheduler
from app.services.intake_service import IntakeService
from app.services.medicine_service import MedicineCreatePayload, MedicineService
from app.services.user_service import UserService
from app.states.medicine_states import AddMedicineStates
from app.utils.datetime_utils import format_days

router = Router()


@router.callback_query(F.data == "medicine_save")
async def medicine_save(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None:
        return
    data = await state.get_data()
    required = {"name", "dosage_text", "time", "days_of_week", "remind_until_confirmed"}
    if not required.issubset(data.keys()):
        await callback.answer("Данные формы устарели. Запустите /add_medicine снова.", show_alert=True)
        await state.clear()
        return
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.answer("Сначала выполните /start", show_alert=True)
            return
        payload = MedicineCreatePayload(
            name=data["name"],
            dosage_text=data["dosage_text"],
            time=data["time"],
            days_of_week=data["days_of_week"],
            remind_until_confirmed=bool(data["remind_until_confirmed"]),
            snooze_minutes=user.default_snooze_minutes,
            comment=data.get("comment"),
        )
        medicine = await MedicineService.create_medicine_with_schedule(session, user, payload)
    await state.clear()
    await callback.message.edit_text(
        f"Сохранено:\n"
        f"- {medicine.name}\n"
        f"- {medicine.dosage_text}\n"
        f"- {payload.time}, {format_days(payload.days_of_week)}"
    )
    scheduler = get_scheduler()
    if scheduler:
        await scheduler.reload_jobs()
    await callback.answer("Лекарство добавлено")


@router.callback_query(F.data == "medicine_edit")
async def medicine_edit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AddMedicineStates.name)
    await callback.message.answer("Введите название лекарства заново:")
    await callback.answer()


@router.callback_query(F.data == "medicine_cancel")
async def medicine_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Добавление отменено.")
    await callback.answer()


@router.callback_query(F.data.startswith("med_toggle:"))
async def medicine_toggle(callback: CallbackQuery) -> None:
    if callback.from_user is None:
        return
    _, medicine_id_str = callback.data.split(":", 1)
    if not medicine_id_str.isdigit():
        await callback.answer("Неверный ID", show_alert=True)
        return
    medicine_id = int(medicine_id_str)
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.answer("Сначала /start", show_alert=True)
            return
        medicine = await MedicineService.get_user_medicine(session, medicine_id, user.id)
        if medicine is None:
            await callback.answer("Лекарство не найдено", show_alert=True)
            return
        new_active = not medicine.is_active
        await MedicineService.set_medicine_active(session, medicine_id, user.id, new_active)
        new_status = "активно" if new_active else "неактивно"
    scheduler = get_scheduler()
    if scheduler:
        await scheduler.reload_jobs()
    await callback.answer("Статус обновлён")
    await callback.message.answer(f"Лекарство ID {medicine_id}: {new_status}")


@router.callback_query(F.data.startswith("med_delete:"))
async def medicine_delete(callback: CallbackQuery) -> None:
    if callback.from_user is None:
        return
    _, medicine_id_str = callback.data.split(":", 1)
    if not medicine_id_str.isdigit():
        await callback.answer("Неверный ID", show_alert=True)
        return
    medicine_id = int(medicine_id_str)
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.answer("Сначала /start", show_alert=True)
            return
        medicine = await MedicineService.get_user_medicine(session, medicine_id, user.id)
        if medicine is None:
            await callback.answer("Лекарство не найдено", show_alert=True)
            return
        medicine_name = medicine.name

    await callback.answer()
    await callback.message.answer(
        f"⚠️ Вы действительно хотите полностью удалить лекарство "
        f"'{medicine_name}' (ID {medicine_id})?\n\n"
        "Действие необратимо: удалятся расписания и история приёмов по этому лекарству.",
        reply_markup=medicine_delete_confirm_keyboard(medicine_id),
    )


@router.callback_query(F.data.startswith("med_delete_confirm:"))
async def medicine_delete_confirm(callback: CallbackQuery) -> None:
    if callback.from_user is None:
        return
    _, medicine_id_str = callback.data.split(":", 1)
    if not medicine_id_str.isdigit():
        await callback.answer("Неверный ID", show_alert=True)
        return
    medicine_id = int(medicine_id_str)
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, callback.from_user.id)
        if user is None:
            await callback.answer("Сначала /start", show_alert=True)
            return
        deleted = await MedicineService.hard_delete_medicine(session, medicine_id, user.id)
        if not deleted:
            await callback.answer("Лекарство не найдено", show_alert=True)
            return

    scheduler = get_scheduler()
    if scheduler:
        await scheduler.reload_jobs()
    await callback.answer("Удалено")
    await callback.message.edit_text(
        f"Лекарство ID {medicine_id} полностью удалено из базы данных.\n"
        "Его расписания и история приёмов также удалены."
    )


@router.callback_query(F.data.startswith("med_delete_cancel:"))
async def medicine_delete_cancel(callback: CallbackQuery) -> None:
    await callback.answer("Удаление отменено")
    await callback.message.edit_text("Удаление отменено.")


@router.callback_query(F.data.startswith("rem:"))
async def reminder_action(callback: CallbackQuery) -> None:
    if callback.from_user is None:
        return
    parts = callback.data.split(":")
    if len(parts) != 5:
        await callback.answer("Некорректные данные", show_alert=True)
        return
    _, action, medicine_id_str, schedule_id_str, scheduled_ts_str = parts
    if not (medicine_id_str.isdigit() and schedule_id_str.isdigit() and scheduled_ts_str.isdigit()):
        await callback.answer("Некорректные параметры", show_alert=True)
        return
    medicine_id = int(medicine_id_str)
    schedule_id = int(schedule_id_str)
    scheduled_at = datetime.fromtimestamp(int(scheduled_ts_str), tz=UTC)

    if action == "snooze":
        async with session_scope() as session:
            user = await UserService.get_by_telegram_id(session, callback.from_user.id)
            if user is None:
                await callback.answer("Сначала /start", show_alert=True)
                return
        scheduler = get_scheduler()
        if scheduler:
            await scheduler.schedule_snooze(medicine_id=medicine_id, schedule_id=schedule_id, minutes=10)
        await callback.answer("Напомню через 10 минут")
        await callback.message.edit_text(f"{callback.message.text}\n\nСтатус: отложено на 10 минут.")
        return

    status = "taken" if action == "taken" else "skipped"
    async with session_scope() as session:
        await IntakeService.log_intake(session, medicine_id=medicine_id, scheduled_at=scheduled_at, status=status)
    label = "принято" if action == "taken" else "пропущено"
    await callback.answer(f"Отмечено: {label}")
    await callback.message.edit_text(f"{callback.message.text}\n\nСтатус: {label}.")

