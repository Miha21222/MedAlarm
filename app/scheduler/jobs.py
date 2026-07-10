from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models import Medicine, MedicineSchedule, ReminderDispatchLog, User
from app.database.session import session_scope
from app.keyboards.inline import reminder_keyboard
from app.services.intake_service import IntakeService
from app.services.schedule_service import ScheduleService
from app.utils.datetime_utils import parse_time_string


class ReminderScheduler:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(timezone=UTC)
        self._bot: Bot | None = None
        self._schedule_fingerprint: tuple[tuple[object, ...], ...] | None = None

    async def start(self, bot: Bot) -> None:
        self._bot = bot
        self._scheduler.start()
        await self.reload_jobs()
        await self.restore_snoozes()
        self._scheduler.add_job(
            self.reconcile_jobs,
            IntervalTrigger(seconds=15),
            id="internal:reconcile",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    async def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    async def reload_jobs(self) -> None:
        async with session_scope() as session:
            schedule_rows = await ScheduleService.get_active_schedule_rows(session)
        for job in self._scheduler.get_jobs():
            if job.id.startswith("schedule:"):
                job.remove()
        for row in schedule_rows:
            self._schedule_row(row.schedule, row.user.timezone)
        self._schedule_fingerprint = self._fingerprint(schedule_rows)

    @staticmethod
    def _fingerprint(schedule_rows: list[object]) -> tuple[tuple[object, ...], ...]:
        return tuple(
            sorted(
                (
                    row.schedule.id,
                    row.schedule.medicine_id,
                    row.schedule.time,
                    row.schedule.days_of_week,
                    row.user.timezone,
                )
                for row in schedule_rows
            )
        )

    async def reconcile_jobs(self) -> None:
        async with session_scope() as session:
            schedule_rows = await ScheduleService.get_active_schedule_rows(session)
        if self._fingerprint(schedule_rows) != self._schedule_fingerprint:
            for job in self._scheduler.get_jobs():
                if job.id.startswith("schedule:"):
                    job.remove()
            for row in schedule_rows:
                self._schedule_row(row.schedule, row.user.timezone)
            self._schedule_fingerprint = self._fingerprint(schedule_rows)

    def _schedule_row(self, schedule: MedicineSchedule, timezone_name: str) -> None:
        hour, minute = parse_time_string(schedule.time)
        if schedule.days_of_week == "*":
            trigger = CronTrigger(hour=hour, minute=minute, timezone=ZoneInfo(timezone_name))
            self._scheduler.add_job(
                self._send_reminder,
                trigger=trigger,
                args=[schedule.medicine_id, schedule.id],
                id=f"schedule:{schedule.id}:daily",
                replace_existing=True,
            )
            return
        for day in [int(part) for part in schedule.days_of_week.split(",") if part]:
            trigger = CronTrigger(hour=hour, minute=minute, day_of_week=str(day), timezone=ZoneInfo(timezone_name))
            self._scheduler.add_job(
                self._send_reminder,
                trigger=trigger,
                args=[schedule.medicine_id, schedule.id],
                id=f"schedule:{schedule.id}:day:{day}",
                replace_existing=True,
            )

    async def schedule_snooze(self, event_id: str, user_id: int, minutes: int) -> datetime:
        run_at = datetime.now(UTC) + timedelta(minutes=minutes)
        should_schedule = True
        async with session_scope() as session:
            dispatch = await session.scalar(
                select(ReminderDispatchLog)
                .join(Medicine, Medicine.id == ReminderDispatchLog.medicine_id)
                .where(ReminderDispatchLog.event_id == event_id, Medicine.user_id == user_id)
            )
            if dispatch is None:
                raise LookupError("reminder event not found")
            if dispatch.resolved_at is not None:
                should_schedule = False
            elif dispatch.status == "snoozed" and dispatch.snoozed_until is not None:
                run_at = dispatch.snoozed_until
                if run_at.tzinfo is None:
                    run_at = run_at.replace(tzinfo=UTC)
            else:
                dispatch.status = "snoozed"
                dispatch.snoozed_until = run_at
        if should_schedule:
            self._schedule_snooze_job(event_id, run_at)
        return run_at

    def _schedule_snooze_job(self, event_id: str, run_at: datetime) -> None:
        trigger = DateTrigger(run_date=run_at)
        self._scheduler.add_job(
            self._send_snoozed_reminder,
            trigger=trigger,
            args=[event_id],
            id=f"snooze:{event_id}",
            replace_existing=True,
        )

    async def restore_snoozes(self) -> None:
        async with session_scope() as session:
            result = await session.execute(
                select(ReminderDispatchLog).where(
                    ReminderDispatchLog.status == "snoozed",
                    ReminderDispatchLog.snoozed_until.is_not(None),
                    ReminderDispatchLog.resolved_at.is_(None),
                )
            )
            snoozes = list(result.scalars())
        now = datetime.now(UTC)
        for dispatch in snoozes:
            run_at = dispatch.snoozed_until
            if run_at is None:
                continue
            if run_at.tzinfo is None:
                run_at = run_at.replace(tzinfo=UTC)
            self._schedule_snooze_job(dispatch.event_id, max(run_at, now))

    async def _send_snoozed_reminder(self, event_id: str) -> None:
        if self._bot is None:
            return
        async with session_scope() as session:
            dispatch = await session.scalar(
                select(ReminderDispatchLog)
                .where(
                    ReminderDispatchLog.event_id == event_id,
                    ReminderDispatchLog.status == "snoozed",
                    ReminderDispatchLog.resolved_at.is_(None),
                )
                .options(
                    selectinload(ReminderDispatchLog.medicine).selectinload(Medicine.user),
                    selectinload(ReminderDispatchLog.schedule),
                )
            )
            if dispatch is None or dispatch.schedule is None or not dispatch.medicine.is_active:
                return
            medicine = dispatch.medicine
            schedule = dispatch.schedule
            user = medicine.user
        text = (
            f"Пора принять лекарство: {medicine.name}\n"
            f"Дозировка: {medicine.dosage_text}\n"
            f"Время по расписанию: {schedule.time}"
        )
        sent_message = await self._bot.send_message(
            chat_id=user.telegram_id,
            text=text,
            reply_markup=reminder_keyboard(
                medicine_id=medicine.id,
                schedule_id=schedule.id,
                scheduled_ts=dispatch.scheduled_ts,
            ),
        )
        async with session_scope() as session:
            current = await session.scalar(
                select(ReminderDispatchLog).where(ReminderDispatchLog.event_id == event_id)
            )
            if current is not None and current.resolved_at is None:
                current.status = "sent"
                current.snoozed_until = None
                current.chat_id = user.telegram_id
                current.message_id = getattr(sent_message, "message_id", None)

    async def _send_reminder(self, medicine_id: int, schedule_id: int) -> None:
        if self._bot is None:
            return
        scheduled_ts = int(datetime.now(UTC).timestamp())
        async with session_scope() as session:
            result = await session.execute(
                select(MedicineSchedule)
                .join(Medicine, Medicine.id == MedicineSchedule.medicine_id)
                .join(User, User.id == Medicine.user_id)
                .where(MedicineSchedule.id == schedule_id, Medicine.id == medicine_id, Medicine.is_active.is_(True))
                .options(
                    selectinload(MedicineSchedule.medicine).selectinload(Medicine.user),
                )
            )
            schedule = result.scalar_one_or_none()
            if schedule is None:
                return
            medicine = schedule.medicine
            user = medicine.user

        text = (
            f"Пора принять лекарство: {medicine.name}\n"
            f"Дозировка: {medicine.dosage_text}\n"
            f"Время по расписанию: {schedule.time}"
        )
        sent_message = await self._bot.send_message(
            chat_id=user.telegram_id,
            text=text,
            reply_markup=reminder_keyboard(medicine_id=medicine.id, schedule_id=schedule.id, scheduled_ts=scheduled_ts),
        )
        async with session_scope() as session:
            await IntakeService.log_dispatch(
                session=session,
                medicine_id=medicine.id,
                schedule_id=schedule.id,
                scheduled_ts=scheduled_ts,
                chat_id=user.telegram_id,
                message_id=getattr(sent_message, "message_id", None),
            )
