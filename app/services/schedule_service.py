from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Medicine, MedicineSchedule, SchedulerState, User


@dataclass(slots=True)
class ScheduleRow:
    schedule: MedicineSchedule
    medicine: Medicine
    user: User


class ScheduleService:
    @staticmethod
    async def generation(session: AsyncSession) -> int:
        value = await session.scalar(
            select(SchedulerState.generation).where(SchedulerState.id == 1)
        )
        return int(value or 0)

    @staticmethod
    async def bump_generation(session: AsyncSession) -> int:
        values = {"id": 1, "generation": 1, "updated_at": datetime.now(UTC)}
        statement = sqlite_insert(SchedulerState).values(**values)
        statement = statement.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "generation": SchedulerState.generation + 1,
                "updated_at": values["updated_at"],
            },
        ).returning(SchedulerState.generation)
        return int((await session.execute(statement)).scalar_one())

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
