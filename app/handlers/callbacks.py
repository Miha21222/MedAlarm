from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.database.session import session_scope
from app.scheduler.setup import get_scheduler
from app.services.intake_service import IntakeService
from app.services.reminder_action_service import ReminderActionService
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
    if action not in {"taken", "skipped", "snooze"}:
        await callback.answer("Некорректное действие", show_alert=True)
        return

    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, callback.from_user.id)
        dispatch = None
        if user is not None:
            dispatch = await IntakeService.get_dispatch(
                session=session,
                medicine_id=medicine_id,
                schedule_id=schedule_id,
                scheduled_ts=scheduled_ts,
                user_id=user.id,
            )
    if dispatch is None or user is None:
        await callback.answer("Это напоминание уже недействительно.", show_alert=True)
        return

    if action == "snooze":
        scheduler = get_scheduler()
        if scheduler is None:
            await callback.answer("Отложить сейчас не удалось. Попробуйте ещё раз.", show_alert=True)
            return
        # Resolve the account setting at click time as well, so callbacks from
        # reminders created before a settings change use the current default.
        minutes = user.default_snooze_minutes
        try:
            await scheduler.schedule_snooze(
                event_id=dispatch.event_id,
                user_id=user.id,
                minutes=minutes,
            )
        except LookupError:
            await callback.answer("Это напоминание уже недействительно.", show_alert=True)
            return
        await callback.answer(f"Напомню через {minutes} минут")
        try:
            await callback.message.edit_text(
                f"{callback.message.text}\n\nСтатус: отложено на {minutes} минут."
            )
        except Exception:
            # Snooze is already persisted; Telegram UI updates are best-effort.
            pass
        return

    status = "taken" if action == "taken" else "skipped"
    try:
        async with session_scope() as session:
            await ReminderActionService.resolve(session, user.id, dispatch.event_id, status)
    except LookupError:
        await callback.answer("Это напоминание уже недействительно.", show_alert=True)
        return

    label = "принято" if action == "taken" else "пропущено"
    await callback.answer(f"Отмечено: {label}")
    try:
        await callback.message.delete()
    except Exception:
        # The action is already persisted; a Telegram deletion failure must not
        # turn an idempotent response into an error or duplicate the intake.
        pass
