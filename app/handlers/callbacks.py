from __future__ import annotations

from datetime import UTC, datetime

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.database.session import session_scope
from app.scheduler.setup import get_scheduler
from app.services.intake_service import IntakeService
from app.services.user_service import UserService

router = Router()


@router.callback_query(F.data.startswith("rem:"))
async def reminder_action(callback: CallbackQuery) -> None:
    if callback.from_user is None or callback.message is None or callback.data is None:
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
    scheduled_ts = int(scheduled_ts_str)
    scheduled_at = datetime.fromtimestamp(scheduled_ts, tz=UTC)
    if action not in {"taken", "skipped", "snooze"}:
        await callback.answer("Некорректное действие", show_alert=True)
        return

    async with session_scope() as session:
        has_dispatch = await IntakeService.has_dispatch(
            session=session,
            medicine_id=medicine_id,
            schedule_id=schedule_id,
            scheduled_ts=scheduled_ts,
        )
    if not has_dispatch:
        await callback.answer("Это напоминание уже недействительно.", show_alert=True)
        return

    if action == "snooze":
        async with session_scope() as session:
            user = await UserService.get_by_telegram_id(session, callback.from_user.id)
            if user is None:
                await callback.answer("Сначала выполните /start", show_alert=True)
                return
        scheduler = get_scheduler()
        if scheduler:
            await scheduler.schedule_snooze(medicine_id=medicine_id, schedule_id=schedule_id, minutes=10)
        await callback.answer("Напомню через 10 минут")
        await callback.message.edit_text(f"{callback.message.text}\n\nСтатус: отложено на 10 минут.")
        return

    status = "taken" if action == "taken" else "skipped"
    async with session_scope() as session:
        await IntakeService.log_intake(
            session=session,
            medicine_id=medicine_id,
            scheduled_at=scheduled_at,
            status=status,
        )

    label = "принято" if action == "taken" else "пропущено"
    await callback.answer(f"Отмечено: {label}")
    await callback.message.edit_text(f"{callback.message.text}\n\nСтатус: {label}.")
