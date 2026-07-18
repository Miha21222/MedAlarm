from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Medicine, MedicineSchedule, User


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
