from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base, Medicine, MedicineSchedule, ReminderDispatchLog, User
from app.scheduler.jobs import ReminderScheduler


class FakeMessage:
    def __init__(self, message_id: int) -> None:
        self.message_id = message_id


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[dict] = []
        self.edits: list[dict] = []

    async def send_message(self, chat_id: int, text: str, reply_markup=None) -> FakeMessage:
        self.messages.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})
        return FakeMessage(len(self.messages))

    async def edit_message_text(self, chat_id: int, message_id: int, text: str, reply_markup=None) -> None:
        self.edits.append(
            {"chat_id": chat_id, "message_id": message_id, "text": text, "reply_markup": reply_markup}
        )


@pytest.mark.asyncio
async def test_send_reminder_sends_message_without_lazy_loading_error(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        user = User(telegram_id=555001, timezone="UTC", default_snooze_minutes=12)
        session.add(user)
        await session.flush()
        medicine = Medicine(user_id=user.id, name="РњР°РіРЅРёР№", dosage_text="1 С‚Р°Р±Р»РµС‚РєР°", is_active=True)
        session.add(medicine)
        await session.flush()
        schedule = MedicineSchedule(
            medicine_id=medicine.id,
            time="15:27",
            days_of_week="*",
            snooze_minutes=25,
            remind_until_confirmed=True,
        )
        session.add(schedule)
        await session.commit()
        medicine_id = medicine.id
        schedule_id = schedule.id

    @asynccontextmanager
    async def fake_session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    monkeypatch.setattr("app.scheduler.jobs.session_scope", fake_session_scope)

    scheduler = ReminderScheduler()
    bot = FakeBot()
    scheduler._bot = bot

    await scheduler._send_reminder(medicine_id=medicine_id, schedule_id=schedule_id)

    assert len(bot.messages) == 1
    callback_data = bot.messages[0]["reply_markup"].inline_keyboard[0][0].callback_data
    assert callback_data is not None
    scheduled_ts = int(callback_data.split(":")[-1])

    async with session_factory() as verify_session:
        dispatch_logs = (
            await verify_session.execute(
                select(ReminderDispatchLog).where(ReminderDispatchLog.medicine_id == medicine_id)
            )
        ).scalars().all()

    assert len(dispatch_logs) == 1
    assert dispatch_logs[0].schedule_id == schedule_id
    assert dispatch_logs[0].scheduled_ts == scheduled_ts
    assert dispatch_logs[0].chat_id == 555001
    assert dispatch_logs[0].message_id == 1

    assert bot.messages[0]["text"]
    assert "15:27" in bot.messages[0]["text"]
    snooze_button = bot.messages[0]["reply_markup"].inline_keyboard[1][0]
    assert snooze_button.text == "⏰ Напомнить через 12 минут"

    await engine.dispose()


@pytest.mark.asyncio
async def test_snooze_is_restored_and_cleared_after_delivery(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        user = User(telegram_id=555002, timezone="UTC", default_snooze_minutes=18)
        session.add(user)
        await session.flush()
        medicine = Medicine(user_id=user.id, name="D3", dosage_text="1", is_active=True)
        session.add(medicine)
        await session.flush()
        schedule = MedicineSchedule(
            medicine_id=medicine.id,
            time="10:00",
            days_of_week="*",
            snooze_minutes=35,
        )
        session.add(schedule)
        await session.flush()
        dispatch = ReminderDispatchLog(
            event_id="evt-restored-snooze",
            medicine_id=medicine.id,
            schedule_id=schedule.id,
            scheduled_ts=int(datetime.now(UTC).timestamp()),
            status="snoozed",
            chat_id=user.telegram_id,
            message_id=42,
            snoozed_until=datetime.now(UTC) + timedelta(minutes=5),
        )
        session.add(dispatch)
        await session.commit()

    @asynccontextmanager
    async def fake_session_scope():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    monkeypatch.setattr("app.scheduler.jobs.session_scope", fake_session_scope)
    scheduler = ReminderScheduler()
    scheduler._bot = FakeBot()

    await scheduler.restore_snoozes()
    assert [job.id for job in scheduler._scheduler.get_jobs()] == ["snooze:evt-restored-snooze"]

    await scheduler._send_snoozed_reminder("evt-restored-snooze")
    async with session_factory() as session:
        restored = await session.scalar(
            select(ReminderDispatchLog).where(ReminderDispatchLog.event_id == "evt-restored-snooze")
        )
    assert restored is not None
    assert restored.status == "sent"
    assert restored.snoozed_until is None
    assert scheduler._bot.messages == []
    assert len(scheduler._bot.edits) == 1
    assert scheduler._bot.edits[0]["chat_id"] == 555002
    assert scheduler._bot.edits[0]["message_id"] == 42
    assert scheduler._bot.edits[0]["reply_markup"] is not None
    snooze_button = scheduler._bot.edits[0]["reply_markup"].inline_keyboard[1][0]
    assert snooze_button.text == "⏰ Напомнить через 18 минут"
    await engine.dispose()
