from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Medicine, MedicineSchedule, User


@dataclass(slots=True)
class MedicineCreatePayload:
    name: str
    dosage_text: str
    time: str
    days_of_week: str
    remind_until_confirmed: bool
    snooze_minutes: int
    comment: str | None = None


class MedicineService:
    @staticmethod
    async def create_medicine_with_schedule(
        session: AsyncSession,
        user: User,
        payload: MedicineCreatePayload,
    ) -> Medicine:
        medicine = Medicine(
            user_id=user.id,
            name=payload.name,
            dosage_text=payload.dosage_text,
            comment=payload.comment,
            is_active=True,
        )
        session.add(medicine)
        await session.flush()
        schedule = MedicineSchedule(
            medicine_id=medicine.id,
            time=payload.time,
            days_of_week=payload.days_of_week,
            snooze_minutes=payload.snooze_minutes,
            remind_until_confirmed=payload.remind_until_confirmed,
        )
        session.add(schedule)
        await session.flush()
        return medicine

    @staticmethod
    async def list_active_medicines(session: AsyncSession, user_id: int) -> list[Medicine]:
        result = await session.execute(
            select(Medicine)
            .options(selectinload(Medicine.schedules))
            .where(Medicine.user_id == user_id, Medicine.is_active.is_(True))
            .order_by(Medicine.created_at.desc())
        )
        return list(result.scalars())

    @staticmethod
    async def list_all_user_medicines(session: AsyncSession, user_id: int) -> list[Medicine]:
        result = await session.execute(
            select(Medicine)
            .options(selectinload(Medicine.schedules))
            .where(Medicine.user_id == user_id)
            .order_by(Medicine.created_at.desc())
        )
        return list(result.scalars())

    @staticmethod
    async def get_user_medicine(session: AsyncSession, medicine_id: int, user_id: int) -> Medicine | None:
        result = await session.execute(select(Medicine).where(Medicine.id == medicine_id, Medicine.user_id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def set_medicine_active(session: AsyncSession, medicine_id: int, user_id: int, is_active: bool) -> bool:
        medicine = await MedicineService.get_user_medicine(session, medicine_id, user_id)
        if medicine is None:
            return False
        medicine.is_active = is_active
        return True

    @staticmethod
    async def soft_delete_medicine(session: AsyncSession, medicine_id: int, user_id: int) -> bool:
        return await MedicineService.set_medicine_active(session, medicine_id, user_id, False)

    @staticmethod
    async def hard_delete_medicine(session: AsyncSession, medicine_id: int, user_id: int) -> bool:
        result = await session.execute(
            select(Medicine)
            .options(
                selectinload(Medicine.schedules),
                selectinload(Medicine.intake_logs),
            )
            .where(Medicine.id == medicine_id, Medicine.user_id == user_id)
        )
        medicine = result.scalar_one_or_none()
        if medicine is None:
            return False
        await session.delete(medicine)
        return True
