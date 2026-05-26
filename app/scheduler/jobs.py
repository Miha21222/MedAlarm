from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.models import Medicine, MedicineSchedule, User
from app.database.session import session_scope
from app.keyboards.inline import reminder_keyboard
from app.services.schedule_service import ScheduleService
from app.utils.datetime_utils import parse_time_string


class ReminderScheduler:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler(timezone=UTC)
        self._bot: Bot | None = None

    async def start(self, bot: Bot) -> None:
        self._bot = bot
        self._scheduler.start()
        await self.reload_jobs()

    async def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    async def reload_jobs(self) -> None:
        self._scheduler.remove_all_jobs()
        async with session_scope() as session:
            schedule_rows = await ScheduleService.get_active_schedule_rows(session)
        for row in schedule_rows:
            self._schedule_row(row.schedule, row.user.timezone)

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

    async def schedule_snooze(self, medicine_id: int, schedule_id: int, minutes: int) -> None:
        run_at = datetime.now(UTC) + timedelta(minutes=minutes)
        trigger = DateTrigger(run_date=run_at)
        self._scheduler.add_job(
            self._send_reminder,
            trigger=trigger,
            args=[medicine_id, schedule_id],
            id=f"snooze:{medicine_id}:{schedule_id}:{int(run_at.timestamp())}",
            replace_existing=False,
        )

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

        scheduled_ts = int(datetime.now(UTC).timestamp())
        text = (
            f"Пора принять лекарство: {medicine.name}\n"
            f"Дозировка: {medicine.dosage_text}\n"
            f"Время по расписанию: {schedule.time}"
        )
        await self._bot.send_message(
            chat_id=user.telegram_id,
            text=text,
            reply_markup=reminder_keyboard(medicine_id=medicine.id, schedule_id=schedule.id, scheduled_ts=scheduled_ts),
        )
