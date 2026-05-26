from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Medicine, MedicineSchedule, User
from app.utils.datetime_utils import is_due_today


@dataclass(slots=True)
class ScheduleRow:
    schedule: MedicineSchedule
    medicine: Medicine
    user: User


class ScheduleService:
    @staticmethod
    async def get_active_schedule_rows(session: AsyncSession) -> list[ScheduleRow]:
        result = await session.execute(
            select(MedicineSchedule)
            .join(Medicine, Medicine.id == MedicineSchedule.medicine_id)
            .join(User, User.id == Medicine.user_id)
            .where(Medicine.is_active.is_(True))
            .options(
                selectinload(MedicineSchedule.medicine).selectinload(Medicine.user),
            )
        )
        rows: list[ScheduleRow] = []
        for schedule in result.scalars():
            rows.append(ScheduleRow(schedule=schedule, medicine=schedule.medicine, user=schedule.medicine.user))
        return rows

    @staticmethod
    async def get_user_today_medicines(session: AsyncSession, user_id: int, target_date: date) -> list[Medicine]:
        medicines_result = await session.execute(
            select(Medicine)
            .where(Medicine.user_id == user_id, Medicine.is_active.is_(True))
            .options(selectinload(Medicine.schedules))
            .order_by(Medicine.name.asc())
        )
        medicines = list(medicines_result.scalars())
        due_medicines: list[Medicine] = []
        for medicine in medicines:
            if any(is_due_today(schedule.days_of_week, target_date) for schedule in medicine.schedules):
                due_medicines.append(medicine)
        return due_medicines

