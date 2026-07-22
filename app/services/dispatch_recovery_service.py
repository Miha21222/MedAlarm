from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import ReminderDispatchLog


@dataclass(frozen=True, slots=True)
class UncertainDispatch:
    event_id: str
    medicine_id: int
    schedule_id: int | None
    scheduled_ts: int
    attempt_count: int
    last_attempt_at: datetime | None
    last_error: str | None
    message_id: int | None


class DispatchRecoveryService:
    """Explicit operator recovery for sends whose Telegram outcome is unknown."""

    @staticmethod
    async def list_uncertain(
        session: AsyncSession,
        *,
        limit: int = 100,
    ) -> list[UncertainDispatch]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        result = await session.execute(
            select(ReminderDispatchLog)
            .where(ReminderDispatchLog.status == "uncertain")
            .order_by(ReminderDispatchLog.last_attempt_at, ReminderDispatchLog.id)
            .limit(limit)
        )
        return [
            UncertainDispatch(
                event_id=row.event_id,
                medicine_id=row.medicine_id,
                schedule_id=row.schedule_id,
                scheduled_ts=row.scheduled_ts,
                attempt_count=row.attempt_count,
                last_attempt_at=row.last_attempt_at,
                last_error=row.last_error,
                message_id=row.message_id,
            )
            for row in result.scalars()
        ]

    @staticmethod
    async def resolve(
        session: AsyncSession,
        *,
        event_id: str,
        action: str,
        note: str,
        message_id: int | None = None,
        now: datetime | None = None,
    ) -> ReminderDispatchLog:
        if action not in {"confirmed_sent", "confirmed_failed"}:
            raise ValueError("unsupported recovery action")
        normalized_note = note.strip()
        if not normalized_note:
            raise ValueError("an operator recovery note is required")
        if len(normalized_note) > 1000:
            raise ValueError("operator recovery note must not exceed 1000 characters")
        if action == "confirmed_sent" and message_id is None:
            raise ValueError("message_id is required when confirming delivery")
        if message_id is not None and message_id <= 0:
            raise ValueError("message_id must be positive")

        dispatch = await session.scalar(
            select(ReminderDispatchLog)
            .where(ReminderDispatchLog.event_id == event_id)
            .with_for_update()
        )
        if dispatch is None:
            raise LookupError("reminder event not found")
        if dispatch.status != "uncertain":
            raise RuntimeError(f"reminder event is {dispatch.status}, not uncertain")

        dispatch.status = "sent" if action == "confirmed_sent" else "failed"
        if message_id is not None:
            dispatch.message_id = message_id
        dispatch.claim_token = None
        dispatch.claim_expires_at = None
        dispatch.snoozed_until = None
        dispatch.recovery_action = action
        dispatch.recovery_note = normalized_note
        dispatch.recovered_at = now or datetime.now(UTC)
        await session.flush()
        return dispatch
