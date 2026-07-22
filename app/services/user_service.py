from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Medicine, MedicineSchedule, User
from app.services.schedule_service import ScheduleService


class UserService:
    @staticmethod
    async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
        result = await session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def register_or_update_user(
        session: AsyncSession,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        default_timezone: str = "UTC",
    ) -> User:
        user = await UserService.get_by_telegram_id(session, telegram_id)
        if user is None:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                timezone=default_timezone,
            )
            session.add(user)
            await session.flush()
            return user
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        return user

    @staticmethod
    async def update_timezone(session: AsyncSession, telegram_id: int, timezone_name: str) -> User | None:
        user = await UserService.get_by_telegram_id(session, telegram_id)
        if user is None:
            return None
        if user.timezone != timezone_name:
            user.timezone = timezone_name
            await ScheduleService.bump_generation(session)
        return user

    @staticmethod
    async def update_snooze_minutes(session: AsyncSession, telegram_id: int, minutes: int) -> User | None:
        user = await UserService.get_by_telegram_id(session, telegram_id)
        if user is None:
            return None
        user.default_snooze_minutes = minutes
        # Snooze is an account preference, not a medicine/device snapshot.
        # Keep legacy schedule rows aligned so existing medicines and API
        # responses immediately reflect the new default without losing IDs or
        # their linked reminder history.
        await session.execute(
            update(MedicineSchedule)
            .where(
                MedicineSchedule.medicine_id.in_(
                    select(Medicine.id).where(Medicine.user_id == user.id)
                )
            )
            .values(snooze_minutes=minutes)
        )
        return user

    @staticmethod
    async def update_repeat_mode(session: AsyncSession, telegram_id: int, remind_until_confirmed: bool) -> User | None:
        user = await UserService.get_by_telegram_id(session, telegram_id)
        if user is None:
            return None
        user.remind_until_confirmed = remind_until_confirmed
        await session.execute(
            update(MedicineSchedule)
            .where(
                MedicineSchedule.medicine_id.in_(
                    select(Medicine.id).where(Medicine.user_id == user.id)
                )
            )
            .values(remind_until_confirmed=remind_until_confirmed)
        )
        return user

