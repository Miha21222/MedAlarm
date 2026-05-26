from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import IntakeLog, Medicine
from app.utils.datetime_utils import period_start


class IntakeService:
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
    ) -> list[IntakeLog]:
        query = (
            select(IntakeLog)
            .join(Medicine, Medicine.id == IntakeLog.medicine_id)
            .where(Medicine.user_id == user_id)
            .options(selectinload(IntakeLog.medicine))
            .order_by(IntakeLog.scheduled_at.desc())
            .limit(limit)
        )
        now_utc = datetime.now(UTC)
        query = query.where(IntakeLog.scheduled_at >= period_start(period, now_utc))
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
            .where(
                Medicine.user_id == user_id,
                IntakeLog.scheduled_at >= start_utc,
                IntakeLog.scheduled_at < end_utc,
            )
            .order_by(IntakeLog.scheduled_at.desc())
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
