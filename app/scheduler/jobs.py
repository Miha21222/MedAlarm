from __future__ import annotations

from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models import Medicine, MedicineSchedule, ReminderDispatchLog, User
from app.database.session import session_scope
from app.keyboards.inline import reminder_keyboard
from app.services.intake_service import IntakeService
from app.services.schedule_service import ScheduleService
from app.services.snooze_service import SnoozeDelivery, SnoozeService
from app.utils.datetime_utils import parse_time_string


class ReminderScheduler:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(timezone=UTC)
        self._bot: Bot | None = None
        self._schedule_fingerprint: tuple[tuple[object, ...], ...] | None = None
        self._schedule_generation = 0
        self._reconcile_ticks = 0

    async def start(self, bot: Bot) -> None:
        self._bot = bot
        self._scheduler.start()
        await self.reload_jobs()
        await self.process_due_snoozes()
        self._scheduler.add_job(
            self.reconcile_jobs,
            IntervalTrigger(seconds=15),
            id="internal:reconcile",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self._scheduler.add_job(
            self.process_due_snoozes,
            IntervalTrigger(seconds=5),
            id="internal:snoozes",
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
            generation = await ScheduleService.generation(session)
        self._replace_schedule_jobs(schedule_rows)
        self._schedule_generation = generation
        self._reconcile_ticks = 0

    def _replace_schedule_jobs(self, schedule_rows: list[object]) -> None:
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
            generation = await ScheduleService.generation(session)
            self._reconcile_ticks += 1
            full_reconcile = self._reconcile_ticks >= 20
            if generation == self._schedule_generation and not full_reconcile:
                return
            schedule_rows = await ScheduleService.get_active_schedule_rows(session)

        fingerprint = self._fingerprint(schedule_rows)
        if generation != self._schedule_generation or fingerprint != self._schedule_fingerprint:
            self._replace_schedule_jobs(schedule_rows)
        self._schedule_generation = generation
        self._reconcile_ticks = 0

    @staticmethod
    def _scheduled_occurrence_ts(
        schedule: MedicineSchedule,
        timezone_name: str,
        now: datetime | None = None,
    ) -> int:
        current = now or datetime.now(UTC)
        zone = ZoneInfo(timezone_name)
        local_now = current.astimezone(zone)
        hour, minute = parse_time_string(schedule.time)
        allowed_days = (
            None
            if schedule.days_of_week == "*"
            else {int(part) for part in schedule.days_of_week.split(",") if part}
        )
        for days_back in range(8):
            local_date = local_now.date() - timedelta(days=days_back)
            if allowed_days is not None and local_date.weekday() not in allowed_days:
                continue
            candidate = datetime.combine(local_date, time(hour, minute), tzinfo=zone)
            if candidate <= local_now + timedelta(minutes=1):
                return int(candidate.astimezone(UTC).timestamp())
        return int(current.timestamp() // 60 * 60)

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

    async def process_due_snoozes(self) -> None:
        if self._bot is None:
            return
        async with session_scope() as session:
            await IntakeService.mark_expired_dispatch_claims_uncertain(session)
            deliveries = await SnoozeService.claim_due(session)
        for delivery in deliveries:
            await self._send_snoozed_reminder(delivery)

    async def _send_snoozed_reminder(self, delivery: SnoozeDelivery) -> None:
        if self._bot is None:
            return
        text = (
            f"Пора принять лекарство: {delivery.medicine_name}\n"
            f"Дозировка: {delivery.dosage_text}\n"
            f"Время по расписанию: {delivery.schedule_time}"
        )
        try:
            await self._bot.edit_message_text(
                chat_id=delivery.chat_id,
                message_id=delivery.message_id,
                text=text,
                reply_markup=reminder_keyboard(
                    medicine_id=delivery.medicine_id,
                    schedule_id=delivery.schedule_id,
                    scheduled_ts=delivery.scheduled_ts,
                    snooze_minutes=delivery.snooze_minutes,
                ),
            )
        except Exception as exc:
            # Editing the same Telegram message is idempotent. Persist a short
            # retry instead of depending on an in-memory APScheduler job.
            async with session_scope() as session:
                await SnoozeService.release(session, delivery, exc)
            return
        async with session_scope() as session:
            await SnoozeService.complete(session, delivery)

    async def _send_reminder(self, medicine_id: int, schedule_id: int) -> None:
        if self._bot is None:
            return
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

        # Derive identity from the intended local cron occurrence rather than
        # worker execution time, so delayed/overlapping workers converge.
        scheduled_ts = self._scheduled_occurrence_ts(schedule, user.timezone)
        text = (
            f"Пора принять лекарство: {medicine.name}\n"
            f"Дозировка: {medicine.dosage_text}\n"
            f"Время по расписанию: {schedule.time}"
        )
        # Commit an atomic ownership claim before sending. A second scheduler
        # observing the same occurrence must return without contacting Telegram.
        async with session_scope() as session:
            dispatch, owned = await IntakeService.claim_dispatch(
                session=session,
                medicine_id=medicine.id,
                schedule_id=schedule.id,
                scheduled_ts=scheduled_ts,
                chat_id=user.telegram_id,
            )
            event_id = dispatch.event_id
            claim_token = dispatch.claim_token
        if not owned or claim_token is None:
            return

        try:
            sent_message = await self._bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                reply_markup=reminder_keyboard(
                    medicine_id=medicine.id,
                    schedule_id=schedule.id,
                    scheduled_ts=scheduled_ts,
                    snooze_minutes=user.default_snooze_minutes,
                ),
            )
        except Exception as exc:
            # Telegram may have accepted a request before the client observed a
            # transport failure. Keep operator-visible uncertain state and do
            # not automatically resend across that crash window.
            async with session_scope() as session:
                failed = await session.scalar(
                    select(ReminderDispatchLog).where(
                        ReminderDispatchLog.event_id == event_id,
                        ReminderDispatchLog.claim_token == claim_token,
                    )
                )
                if failed is not None:
                    failed.status = "uncertain"
                    failed.claim_token = None
                    failed.claim_expires_at = None
                    failed.last_error = str(exc)[:1000]
            raise

        async with session_scope() as session:
            delivered = await session.scalar(
                select(ReminderDispatchLog).where(ReminderDispatchLog.event_id == event_id)
            )
            if delivered is not None and delivered.claim_token == claim_token:
                delivered.status = "sent"
                delivered.message_id = getattr(sent_message, "message_id", None)
                delivered.claim_token = None
                delivered.claim_expires_at = None
                delivered.last_error = None
