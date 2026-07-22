from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import IntakeLog, Medicine, MedicineSchedule, ReminderDispatchLog
from app.utils.datetime_utils import is_due_today, is_schedule_available_on_creation_day, period_range


@dataclass(slots=True)
class TodayDose:
    medicine: Medicine
    schedule: MedicineSchedule
    scheduled_at: datetime
    status: str
    event_id: str | None
    actionable: bool


class IntakeService:
    @staticmethod
    async def today_doses(
        session: AsyncSession,
        user_id: int,
        local_date: date,
        timezone_name: str,
    ) -> list[TodayDose]:
        tz = ZoneInfo(timezone_name)
        start_local = datetime.combine(local_date, time.min, tzinfo=tz)
        end_local = start_local + timedelta(days=1)
        start_ts = int(start_local.astimezone(UTC).timestamp())
        end_ts = int(end_local.astimezone(UTC).timestamp())

        schedule_result = await session.execute(
            select(MedicineSchedule)
            .join(Medicine, Medicine.id == MedicineSchedule.medicine_id)
            .where(Medicine.user_id == user_id, Medicine.is_active.is_(True))
            .options(
                selectinload(MedicineSchedule.medicine).selectinload(Medicine.schedules)
            )
        )
        schedules = [
            schedule
            for schedule in schedule_result.scalars()
            if is_due_today(schedule.days_of_week, local_date)
            and is_schedule_available_on_creation_day(
                schedule.medicine.created_at,
                schedule.time,
                local_date,
                timezone_name,
            )
        ]

        dispatch_result = await session.execute(
            select(ReminderDispatchLog)
            .join(Medicine, Medicine.id == ReminderDispatchLog.medicine_id)
            .where(
                Medicine.user_id == user_id,
                ReminderDispatchLog.scheduled_ts >= start_ts,
                ReminderDispatchLog.scheduled_ts < end_ts,
            )
            .order_by(ReminderDispatchLog.scheduled_ts.desc())
        )
        dispatch_by_schedule: dict[int, ReminderDispatchLog] = {}
        for dispatch in dispatch_result.scalars():
            if dispatch.schedule_id is not None and dispatch.schedule_id not in dispatch_by_schedule:
                dispatch_by_schedule[dispatch.schedule_id] = dispatch

        dispatch_ids = [dispatch.id for dispatch in dispatch_by_schedule.values()]
        intake_by_dispatch: dict[int, IntakeLog] = {}
        if dispatch_ids:
            intake_result = await session.execute(
                select(IntakeLog).where(IntakeLog.reminder_event_id.in_(dispatch_ids))
            )
            intake_by_dispatch = {
                intake.reminder_event_id: intake
                for intake in intake_result.scalars()
                if intake.reminder_event_id is not None
            }

        doses: list[TodayDose] = []
        for schedule in schedules:
            hour, minute = (int(part) for part in schedule.time.split(":"))
            scheduled_at = datetime.combine(local_date, time(hour, minute), tzinfo=tz).astimezone(UTC)
            dispatch = dispatch_by_schedule.get(schedule.id)
            intake = intake_by_dispatch.get(dispatch.id) if dispatch is not None else None
            status = intake.status if intake is not None else (
                "snoozed" if dispatch is not None and dispatch.status == "snoozed" else "pending"
            )
            doses.append(
                TodayDose(
                    medicine=schedule.medicine,
                    schedule=schedule,
                    scheduled_at=scheduled_at,
                    status=status,
                    event_id=dispatch.event_id if dispatch is not None else None,
                    actionable=(
                        dispatch is not None
                        and dispatch.resolved_at is None
                        and dispatch.status in {"sent", "snoozed"}
                    ),
                )
            )
        doses.sort(key=lambda dose: (dose.scheduled_at, dose.schedule.id))
        return doses

    @staticmethod
    async def log_dispatch(
        session: AsyncSession,
        *,
        medicine_id: int,
        schedule_id: int,
        scheduled_ts: int,
        chat_id: int | None = None,
        message_id: int | None = None,
    ) -> ReminderDispatchLog:
        dispatch = ReminderDispatchLog(
            medicine_id=medicine_id,
            schedule_id=schedule_id,
            scheduled_ts=scheduled_ts,
            chat_id=chat_id,
            message_id=message_id,
            sent_at=datetime.now(UTC),
        )
        session.add(dispatch)
        await session.flush()
        return dispatch

    @staticmethod
    async def claim_dispatch(
        session: AsyncSession,
        *,
        medicine_id: int,
        schedule_id: int,
        scheduled_ts: int,
        chat_id: int,
        lease_seconds: int = 120,
    ) -> tuple[ReminderDispatchLog, bool]:
        """Create and own one schedule occurrence without a duplicate-send race."""
        now = datetime.now(UTC)
        event_id = str(uuid.uuid4())
        claim_token = str(uuid.uuid4())
        values = {
            "event_id": event_id,
            "medicine_id": medicine_id,
            "schedule_id": schedule_id,
            "scheduled_ts": scheduled_ts,
            "status": "sending",
            "chat_id": chat_id,
            "claim_token": claim_token,
            "claim_expires_at": now + timedelta(seconds=lease_seconds),
            "attempt_count": 1,
            "last_attempt_at": now,
            "sent_at": now,
        }
        statement = sqlite_insert(ReminderDispatchLog).values(**values)
        statement = statement.on_conflict_do_nothing(
            index_elements=["schedule_id", "scheduled_ts"]
        )
        inserted = await session.execute(statement)
        dispatch = await session.scalar(
            select(ReminderDispatchLog).where(
                ReminderDispatchLog.schedule_id == schedule_id,
                ReminderDispatchLog.scheduled_ts == scheduled_ts,
            )
        )
        if dispatch is None:  # pragma: no cover - defensive transaction check
            raise RuntimeError("dispatch claim was not visible after insert")
        return dispatch, inserted.rowcount == 1 and dispatch.event_id == event_id

    @staticmethod
    async def mark_expired_dispatch_claims_uncertain(
        session: AsyncSession,
        *,
        now: datetime | None = None,
    ) -> int:
        result = await session.execute(
            update(ReminderDispatchLog)
            .where(
                ReminderDispatchLog.status == "sending",
                ReminderDispatchLog.snoozed_until.is_(None),
                ReminderDispatchLog.claim_expires_at <= (now or datetime.now(UTC)),
            )
            .values(
                status="uncertain",
                claim_token=None,
                claim_expires_at=None,
                last_error="dispatch claim expired before delivery acknowledgement",
            )
            .execution_options(synchronize_session=False)
        )
        return result.rowcount

    @staticmethod
    async def get_dispatch(
        session: AsyncSession,
        *,
        medicine_id: int,
        schedule_id: int,
        scheduled_ts: int,
        user_id: int | None = None,
    ) -> ReminderDispatchLog | None:
        query = (
            select(ReminderDispatchLog)
            .where(
                ReminderDispatchLog.medicine_id == medicine_id,
                ReminderDispatchLog.schedule_id == schedule_id,
                ReminderDispatchLog.scheduled_ts == scheduled_ts,
            )
            .options(selectinload(ReminderDispatchLog.schedule))
        )
        if user_id is not None:
            query = query.join(Medicine, Medicine.id == ReminderDispatchLog.medicine_id).where(
                Medicine.user_id == user_id
            )
        return await session.scalar(query)

    @staticmethod
    async def has_dispatch(
        session: AsyncSession,
        *,
        medicine_id: int,
        schedule_id: int,
        scheduled_ts: int,
    ) -> bool:
        result = await session.execute(
            select(ReminderDispatchLog.id).where(
                ReminderDispatchLog.medicine_id == medicine_id,
                ReminderDispatchLog.schedule_id == schedule_id,
                ReminderDispatchLog.scheduled_ts == scheduled_ts,
            )
        )
        return result.scalar_one_or_none() is not None

    @staticmethod
    async def log_intake(session: AsyncSession, medicine_id: int, scheduled_at: datetime, status: str) -> IntakeLog:
        intake = IntakeLog(
            medicine_id=medicine_id,
            scheduled_at=scheduled_at,
            status=status,
            responded_at=datetime.now(UTC),
        )
        session.add(intake)
        await session.flush()
        return intake

    @staticmethod
    async def history(
        session: AsyncSession,
        user_id: int,
        period: str = "week",
        medicine_id: int | None = None,
        limit: int = 50,
        timezone_name: str = "UTC",
    ) -> list[IntakeLog]:
        query = (
            select(IntakeLog)
            .join(Medicine, Medicine.id == IntakeLog.medicine_id)
            .join(ReminderDispatchLog, ReminderDispatchLog.id == IntakeLog.reminder_event_id)
            .where(
                Medicine.user_id == user_id,
                ReminderDispatchLog.medicine_id == IntakeLog.medicine_id,
            )
            .options(selectinload(IntakeLog.medicine))
            .order_by(IntakeLog.responded_at.desc())
            .limit(limit)
        )
        period_start, period_end = period_range(period, datetime.now(UTC), timezone_name)
        query = query.where(IntakeLog.responded_at >= period_start)
        if period_end is not None:
            query = query.where(IntakeLog.responded_at < period_end)
        if medicine_id is not None:
            query = query.where(IntakeLog.medicine_id == medicine_id)
        result = await session.execute(query)
        return list(result.scalars())

    @staticmethod
    async def today_status_by_medicine(
        session: AsyncSession,
        user_id: int,
        local_date: date,
        timezone_name: str,
    ) -> dict[int, str]:
        tz = ZoneInfo(timezone_name)
        start_local = datetime.combine(local_date, time.min, tzinfo=tz)
        end_local = start_local + timedelta(days=1)
        start_utc = start_local.astimezone(UTC)
        end_utc = end_local.astimezone(UTC)
        result = await session.execute(
            select(IntakeLog)
            .join(Medicine, Medicine.id == IntakeLog.medicine_id)
            .join(ReminderDispatchLog, ReminderDispatchLog.id == IntakeLog.reminder_event_id)
            .where(
                Medicine.user_id == user_id,
                ReminderDispatchLog.medicine_id == IntakeLog.medicine_id,
                IntakeLog.responded_at >= start_utc,
                IntakeLog.responded_at < end_utc,
            )
            .order_by(IntakeLog.responded_at.desc())
        )
        logs = list(result.scalars())
        status_by_medicine: dict[int, str] = {}
        for log in logs:
            if log.medicine_id not in status_by_medicine:
                status_by_medicine[log.medicine_id] = log.status
        return status_by_medicine

    @staticmethod
    def status_to_emoji(status: str) -> str:
        mapping = {
            "taken": "✅",
            "skipped": "❌",
            "missed": "⏭️",
        }
        return mapping.get(status, "❔")
