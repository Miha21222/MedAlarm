from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base, Medicine, MedicineSchedule, ReminderDispatchLog, User
from app.services.snooze_service import SnoozeService


@pytest.mark.asyncio
async def test_durable_snooze_request_and_claim_are_idempotent():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    now = datetime.now(UTC)
    async with sessions() as session:
        user = User(telegram_id=7000000001, default_snooze_minutes=10)
        session.add(user)
        await session.flush()
        medicine = Medicine(user_id=user.id, name="Test", dosage_text="1", is_active=True)
        session.add(medicine)
        await session.flush()
        schedule = MedicineSchedule(medicine_id=medicine.id, time="08:00", days_of_week="*")
        session.add(schedule)
        await session.flush()
        dispatch = ReminderDispatchLog(
            event_id="evt-durable",
            medicine_id=medicine.id,
            schedule_id=schedule.id,
            scheduled_ts=int(now.timestamp()),
            status="sent",
            chat_id=user.telegram_id,
            message_id=10,
        )
        session.add(dispatch)
        await session.commit()
        user_id = user.id

    async with sessions() as session:
        first = await SnoozeService.request(
            session, event_id="evt-durable", user_id=user_id, minutes=10, now=now
        )
        second = await SnoozeService.request(
            session, event_id="evt-durable", user_id=user_id, minutes=30, now=now
        )
        await session.commit()
    assert first == second

    due = first + timedelta(seconds=1)
    async with sessions() as session:
        claimed = await SnoozeService.claim_due(session, now=due, lease_seconds=60)
        await session.commit()
    assert len(claimed) == 1

    async with sessions() as session:
        duplicate = await SnoozeService.claim_due(session, now=due, lease_seconds=60)
    assert duplicate == []

    async with sessions() as session:
        recovered = await SnoozeService.claim_due(
            session, now=due + timedelta(seconds=61), lease_seconds=60
        )
        await session.commit()
    assert len(recovered) == 1
    assert recovered[0].claim_token != claimed[0].claim_token

    async with sessions() as session:
        assert await SnoozeService.complete(session, recovered[0]) is True
        await session.commit()
        stored = await session.scalar(
            select(ReminderDispatchLog).where(ReminderDispatchLog.event_id == "evt-durable")
        )
    assert stored is not None
    assert stored.status == "sent"
    assert stored.snoozed_until is None
    assert stored.attempt_count == 2
    await engine.dispose()
