from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import IntakeLog, Medicine, ReminderDispatchLog


@dataclass(slots=True)
class ReminderActionResult:
    event_id: str
    status: str
    intake_id: int


class ReminderActionService:
    @staticmethod
    async def resolve(
        session: AsyncSession,
        user_id: int,
        event_id: str,
        action: str,
    ) -> ReminderActionResult:
        if action not in {"taken", "skipped"}:
            raise ValueError("unsupported reminder action")

        event = await session.scalar(
            select(ReminderDispatchLog)
            .join(Medicine, Medicine.id == ReminderDispatchLog.medicine_id)
            .where(
                ReminderDispatchLog.event_id == event_id,
                Medicine.user_id == user_id,
            )
        )
        if event is None:
            raise LookupError("reminder event not found")

        existing = await session.scalar(
            select(IntakeLog).where(IntakeLog.reminder_event_id == event.id)
        )
        if existing is not None:
            return ReminderActionResult(event.event_id, existing.status, existing.id)

        scheduled_at = datetime.fromtimestamp(event.scheduled_ts, tz=UTC)
        intake = IntakeLog(
            medicine_id=event.medicine_id,
            reminder_event_id=event.id,
            scheduled_at=scheduled_at,
            status=action,
            responded_at=datetime.now(UTC),
        )
        session.add(intake)
        event.status = action
        event.resolved_at = datetime.now(UTC)
        await session.flush()
        return ReminderActionResult(event.event_id, action, intake.id)
