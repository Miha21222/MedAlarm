from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Medicine, MedicineSchedule, User
from app.services.schedule_service import ScheduleService


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@dataclass(slots=True)
class ScheduleSyncPayload:
    time: str
    days_of_week: str = "*"
    snooze_minutes: int | None = None
    remind_until_confirmed: bool | None = None


@dataclass(slots=True)
class MedicineSyncPayload:
    client_medicine_id: str
    name: str
    dosage_text: str
    comment: str | None
    is_active: bool
    updated_at: datetime
    deleted_at: datetime | None
    schedules: list[ScheduleSyncPayload]
    catalog: dict[str, object] | None = None
    created_at: datetime | None = None


class MedicineSyncService:
    @staticmethod
    async def apply(
        session: AsyncSession,
        user: User,
        payload: MedicineSyncPayload,
    ) -> tuple[bool, Medicine]:
        medicine = await session.scalar(
            select(Medicine)
            .where(
                Medicine.user_id == user.id,
                Medicine.client_medicine_id == payload.client_medicine_id,
            )
            .options(selectinload(Medicine.schedules))
        )
        incoming_updated_at = _utc(payload.updated_at)
        if medicine is not None and _utc(medicine.updated_at) >= incoming_updated_at:
            return False, medicine

        if medicine is None:
            medicine = Medicine(
                user_id=user.id,
                client_medicine_id=payload.client_medicine_id,
                name=payload.name,
                dosage_text=payload.dosage_text,
                created_at=_utc(payload.created_at or payload.updated_at),
            )
            session.add(medicine)
        medicine.name = payload.name.strip()
        medicine.dosage_text = payload.dosage_text.strip()
        medicine.comment = payload.comment
        medicine.catalog_snapshot = payload.catalog
        medicine.is_active = payload.is_active and payload.deleted_at is None
        medicine.updated_at = incoming_updated_at
        medicine.deleted_at = _utc(payload.deleted_at) if payload.deleted_at else None

        # Reconcile slots in place instead of clear-and-reinsert. SQLAlchemy may
        # issue INSERTs before orphan DELETEs during one flush, which collides
        # with uq_schedule_slot when an unchanged slot is synced again. Keeping
        # matching rows also preserves their IDs and reminder-event links.
        incoming_by_key = {
            (slot.time, slot.days_of_week): slot
            for slot in payload.schedules
        }
        for schedule in list(medicine.schedules):
            slot = incoming_by_key.pop((schedule.time, schedule.days_of_week), None)
            if slot is None:
                medicine.schedules.remove(schedule)
                continue
            # Snooze is account-owned. Ignore stale per-device/per-medicine
            # snapshots so every existing and future slot follows settings.
            schedule.snooze_minutes = user.default_snooze_minutes
            schedule.remind_until_confirmed = (
                user.remind_until_confirmed
                if slot.remind_until_confirmed is None
                else slot.remind_until_confirmed
            )
        for key in sorted(incoming_by_key):
            slot = incoming_by_key[key]
            medicine.schedules.append(
                MedicineSchedule(
                    time=slot.time,
                    days_of_week=slot.days_of_week,
                    snooze_minutes=user.default_snooze_minutes,
                    remind_until_confirmed=(
                        user.remind_until_confirmed
                        if slot.remind_until_confirmed is None
                        else slot.remind_until_confirmed
                    ),
                )
            )
        await session.flush()
        await ScheduleService.bump_generation(session)
        return True, medicine
