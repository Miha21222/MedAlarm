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
    times: list[str]
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
        for schedule_time in payload.times:
            session.add(
                MedicineSchedule(
                    medicine_id=medicine.id,
                    time=schedule_time,
                    days_of_week=payload.days_of_week,
                    snooze_minutes=payload.snooze_minutes,
                    remind_until_confirmed=payload.remind_until_confirmed,
                )
            )
        await session.flush()
        return medicine

    @staticmethod
    async def update_medicine_with_schedule(
        session: AsyncSession,
        medicine: Medicine,
        payload: MedicineCreatePayload,
    ) -> Medicine:
        medicine.name = payload.name
        medicine.dosage_text = payload.dosage_text
        medicine.comment = payload.comment
        await session.flush()
        schedules_result = await session.execute(
            select(MedicineSchedule).where(MedicineSchedule.medicine_id == medicine.id)
        )
        for schedule in schedules_result.scalars():
            await session.delete(schedule)
        await session.flush()
        for schedule_time in payload.times:
            session.add(
                MedicineSchedule(
                    medicine_id=medicine.id,
                    time=schedule_time,
                    days_of_week=payload.days_of_week,
                    snooze_minutes=payload.snooze_minutes,
                    remind_until_confirmed=payload.remind_until_confirmed,
                )
            )
        await session.flush()
        return medicine

    @staticmethod
    async def update_medicine_name(session: AsyncSession, medicine: Medicine, name: str) -> Medicine:
        medicine.name = name
        await session.flush()
        return medicine

    @staticmethod
    async def update_medicine_dosage(session: AsyncSession, medicine: Medicine, dosage_text: str) -> Medicine:
        medicine.dosage_text = dosage_text
        await session.flush()
        return medicine

    @staticmethod
    async def update_medicine_comment(session: AsyncSession, medicine: Medicine, comment: str | None) -> Medicine:
        medicine.comment = comment
        await session.flush()
        return medicine

    @staticmethod
    async def update_schedule_fields(
        session: AsyncSession,
        medicine: Medicine,
        *,
        times: list[str] | None = None,
        days_of_week: str | None = None,
        remind_until_confirmed: bool | None = None,
        snooze_minutes: int | None = None,
    ) -> Medicine:
        schedules_result = await session.execute(
            select(MedicineSchedule).where(MedicineSchedule.medicine_id == medicine.id)
        )
        schedules = list(schedules_result.scalars())
        if not schedules:
            return medicine

        current_times = sorted(schedule.time for schedule in schedules)
        current_days = schedules[0].days_of_week
        current_repeat = schedules[0].remind_until_confirmed
        current_snooze = schedules[0].snooze_minutes

        new_times = times if times is not None else current_times
        new_days = days_of_week if days_of_week is not None else current_days
        new_repeat = remind_until_confirmed if remind_until_confirmed is not None else current_repeat
        new_snooze = snooze_minutes if snooze_minutes is not None else current_snooze

        for schedule in schedules:
            await session.delete(schedule)
        await session.flush()
        for schedule_time in sorted(new_times):
            session.add(
                MedicineSchedule(
                    medicine_id=medicine.id,
                    time=schedule_time,
                    days_of_week=new_days,
                    snooze_minutes=new_snooze,
                    remind_until_confirmed=new_repeat,
                )
            )
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
        medicines = list(result.scalars())
        for medicine in medicines:
            medicine.schedules.sort(key=lambda schedule: schedule.time)
        return medicines

    @staticmethod
    async def list_all_user_medicines(session: AsyncSession, user_id: int) -> list[Medicine]:
        result = await session.execute(
            select(Medicine)
            .options(selectinload(Medicine.schedules))
            .where(Medicine.user_id == user_id)
            .order_by(Medicine.id.asc())
        )
        medicines = list(result.scalars())
        for medicine in medicines:
            medicine.schedules.sort(key=lambda schedule: schedule.time)
        return medicines

    @staticmethod
    async def get_user_medicine(session: AsyncSession, medicine_id: int, user_id: int) -> Medicine | None:
        result = await session.execute(
            select(Medicine)
            .options(selectinload(Medicine.schedules))
            .where(Medicine.id == medicine_id, Medicine.user_id == user_id)
        )
        medicine = result.scalar_one_or_none()
        if medicine:
            medicine.schedules.sort(key=lambda schedule: schedule.time)
        return medicine

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
