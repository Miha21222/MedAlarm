from __future__ import annotations

from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.models import Base, Medicine, MedicineSchedule, User
from app.scheduler.jobs import ReminderScheduler


class FakeBot:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_message(self, chat_id: int, text: str, reply_markup=None) -> None:
        self.messages.append({"chat_id": chat_id, "text": text, "reply_markup": reply_markup})


@pytest.mark.asyncio
async def test_send_reminder_sends_message_without_lazy_loading_error(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        user = User(telegram_id=555001, timezone="UTC")
        session.add(user)
        await session.flush()
        medicine = Medicine(user_id=user.id, name="Магний", dosage_text="1 таблетка", is_active=True)
        session.add(medicine)
        await session.flush()
        schedule = MedicineSchedule(
            medicine_id=medicine.id,
            time="15:27",
            days_of_week="*",
            snooze_minutes=10,
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
    assert "Пора принять лекарство" in bot.messages[0]["text"]

    await engine.dispose()

