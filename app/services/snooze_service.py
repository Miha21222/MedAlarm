from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Medicine, ReminderDispatchLog


@dataclass(frozen=True, slots=True)
class SnoozeDelivery:
    event_id: str
    claim_token: str
    medicine_id: int
    medicine_name: str
    dosage_text: str
    schedule_id: int
    schedule_time: str
    scheduled_ts: int
    chat_id: int
    message_id: int
    snooze_minutes: int


class SnoozeService:
    """Durable snooze state shared by bot callbacks and the scheduler process."""

    @staticmethod
    async def request(
        session: AsyncSession,
        *,
        event_id: str,
        user_id: int,
        minutes: int,
        now: datetime | None = None,
    ) -> datetime:
        current_time = now or datetime.now(UTC)
        dispatch = await session.scalar(
            select(ReminderDispatchLog)
            .join(Medicine, Medicine.id == ReminderDispatchLog.medicine_id)
            .where(ReminderDispatchLog.event_id == event_id, Medicine.user_id == user_id)
            .with_for_update()
        )
        if dispatch is None or dispatch.resolved_at is not None:
            raise LookupError("reminder event not found")
        if dispatch.status in {"snoozed", "sending"} and dispatch.snoozed_until is not None:
            run_at = dispatch.snoozed_until
            return run_at.replace(tzinfo=UTC) if run_at.tzinfo is None else run_at

        run_at = current_time + timedelta(minutes=minutes)
        dispatch.status = "snoozed"
        dispatch.snoozed_until = run_at
        dispatch.claim_token = None
        dispatch.claim_expires_at = None
        dispatch.last_error = None
        return run_at

    @staticmethod
    async def claim_due(
        session: AsyncSession,
        *,
        now: datetime | None = None,
        lease_seconds: int = 120,
        limit: int = 20,
    ) -> list[SnoozeDelivery]:
        current_time = now or datetime.now(UTC)
        eligible = or_(
            and_(
                ReminderDispatchLog.status == "snoozed",
                ReminderDispatchLog.snoozed_until <= current_time,
            ),
            and_(
                ReminderDispatchLog.status == "sending",
                ReminderDispatchLog.snoozed_until.is_not(None),
                ReminderDispatchLog.claim_expires_at <= current_time,
            ),
        )
        result = await session.execute(
            select(ReminderDispatchLog)
            .where(
                ReminderDispatchLog.resolved_at.is_(None),
                ReminderDispatchLog.snoozed_until.is_not(None),
                eligible,
            )
            .order_by(ReminderDispatchLog.snoozed_until, ReminderDispatchLog.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
            .options(
                selectinload(ReminderDispatchLog.medicine).selectinload(Medicine.user),
                selectinload(ReminderDispatchLog.schedule),
            )
        )

        deliveries: list[SnoozeDelivery] = []
        for dispatch in result.scalars():
            if (
                dispatch.schedule is None
                or not dispatch.medicine.is_active
                or dispatch.chat_id is None
                or dispatch.message_id is None
            ):
                dispatch.status = "failed"
                dispatch.snoozed_until = None
                dispatch.claim_token = None
                dispatch.claim_expires_at = None
                dispatch.last_error = "durable snooze is no longer deliverable"
                continue
            token = str(uuid.uuid4())
            claimed = await session.execute(
                update(ReminderDispatchLog)
                .where(
                    ReminderDispatchLog.id == dispatch.id,
                    ReminderDispatchLog.resolved_at.is_(None),
                    eligible,
                )
                .values(
                    status="sending",
                    claim_token=token,
                    claim_expires_at=current_time + timedelta(seconds=lease_seconds),
                    attempt_count=ReminderDispatchLog.attempt_count + 1,
                    last_attempt_at=current_time,
                    last_error=None,
                )
                .execution_options(synchronize_session=False)
            )
            if claimed.rowcount != 1:
                continue
            deliveries.append(
                SnoozeDelivery(
                    event_id=dispatch.event_id,
                    claim_token=token,
                    medicine_id=dispatch.medicine.id,
                    medicine_name=dispatch.medicine.name,
                    dosage_text=dispatch.medicine.dosage_text,
                    schedule_id=dispatch.schedule.id,
                    schedule_time=dispatch.schedule.time,
                    scheduled_ts=dispatch.scheduled_ts,
                    chat_id=dispatch.chat_id,
                    message_id=dispatch.message_id,
                    snooze_minutes=dispatch.medicine.user.default_snooze_minutes,
                )
            )
        return deliveries

    @staticmethod
    async def complete(session: AsyncSession, delivery: SnoozeDelivery) -> bool:
        result = await session.execute(
            update(ReminderDispatchLog)
            .where(
                ReminderDispatchLog.event_id == delivery.event_id,
                ReminderDispatchLog.claim_token == delivery.claim_token,
                ReminderDispatchLog.resolved_at.is_(None),
            )
            .values(
                status="sent",
                snoozed_until=None,
                claim_token=None,
                claim_expires_at=None,
                last_error=None,
            )
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    @staticmethod
    async def release(
        session: AsyncSession,
        delivery: SnoozeDelivery,
        error: Exception,
        *,
        retry_at: datetime | None = None,
    ) -> bool:
        result = await session.execute(
            update(ReminderDispatchLog)
            .where(
                ReminderDispatchLog.event_id == delivery.event_id,
                ReminderDispatchLog.claim_token == delivery.claim_token,
                ReminderDispatchLog.resolved_at.is_(None),
            )
            .values(
                status="snoozed",
                snoozed_until=retry_at or (datetime.now(UTC) + timedelta(seconds=30)),
                claim_token=None,
                claim_expires_at=None,
                last_error=str(error)[:1000],
            )
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1
