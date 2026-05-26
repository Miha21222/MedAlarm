from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.database.models import IntakeLog, Medicine, MedicineSchedule, User
from app.services.intake_service import IntakeService
from app.services.medicine_service import MedicineCreatePayload, MedicineService
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_register_user_idempotent(db_session):
    user1 = await UserService.register_or_update_user(
        session=db_session,
        telegram_id=12345,
        username="test",
        first_name="A",
        last_name="B",
        default_timezone="UTC",
    )
    await db_session.commit()
    user2 = await UserService.register_or_update_user(
        session=db_session,
        telegram_id=12345,
        username="newname",
        first_name="A2",
        last_name="B2",
        default_timezone="UTC",
    )
    await db_session.commit()
    assert user1.id == user2.id
    assert user2.username == "newname"


@pytest.mark.asyncio
async def test_create_medicine_and_list_active(db_session):
    user = User(telegram_id=9988, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    payload = MedicineCreatePayload(
        name="Магний",
        dosage_text="1 таблетка",
        time="21:00",
        days_of_week="*",
        remind_until_confirmed=True,
        snooze_minutes=10,
    )
    medicine = await MedicineService.create_medicine_with_schedule(db_session, user, payload)
    await db_session.commit()
    meds = await MedicineService.list_active_medicines(db_session, user.id)
    assert len(meds) == 1
    assert meds[0].id == medicine.id
    assert meds[0].schedules[0].time == "21:00"


@pytest.mark.asyncio
async def test_history_filters_by_period(db_session):
    user = User(telegram_id=7788, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    payload = MedicineCreatePayload(
        name="Омега-3",
        dosage_text="1 капсула",
        time="09:00",
        days_of_week="*",
        remind_until_confirmed=True,
        snooze_minutes=10,
    )
    medicine = await MedicineService.create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    await IntakeService.log_intake(
        db_session, medicine.id, datetime.now(UTC) - timedelta(days=2), "taken"
    )
    await IntakeService.log_intake(
        db_session, medicine.id, datetime.now(UTC) - timedelta(days=40), "skipped"
    )
    await db_session.commit()

    week_history = await IntakeService.history(db_session, user.id, period="week")
    month_history = await IntakeService.history(db_session, user.id, period="month")
    assert len(week_history) == 1
    assert len(month_history) == 1


@pytest.mark.asyncio
async def test_hard_delete_medicine_removes_related_rows(db_session):
    user = User(telegram_id=1122, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    payload = MedicineCreatePayload(
        name="Витамин D",
        dosage_text="1 капсула",
        time="08:00",
        days_of_week="*",
        remind_until_confirmed=True,
        snooze_minutes=10,
    )
    medicine = await MedicineService.create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    await IntakeService.log_intake(
        db_session,
        medicine_id=medicine.id,
        scheduled_at=datetime.now(UTC),
        status="taken",
    )
    await db_session.commit()

    deleted = await MedicineService.hard_delete_medicine(db_session, medicine.id, user.id)
    await db_session.commit()
    assert deleted is True

    medicine_count = await db_session.scalar(select(func.count()).select_from(Medicine))
    schedule_count = await db_session.scalar(select(func.count()).select_from(MedicineSchedule))
    intake_count = await db_session.scalar(select(func.count()).select_from(IntakeLog))
    assert medicine_count == 0
    assert schedule_count == 0
    assert intake_count == 0


@pytest.mark.asyncio
async def test_today_status_by_medicine_uses_latest_status(db_session):
    user = User(telegram_id=4242, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    payload = MedicineCreatePayload(
        name="Магний",
        dosage_text="1 таблетка",
        time="10:00",
        days_of_week="*",
        remind_until_confirmed=True,
        snooze_minutes=10,
    )
    medicine = await MedicineService.create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    now = datetime.now(UTC)
    await IntakeService.log_intake(db_session, medicine.id, now - timedelta(hours=2), "skipped")
    await IntakeService.log_intake(db_session, medicine.id, now - timedelta(hours=1), "taken")
    await db_session.commit()

    status_map = await IntakeService.today_status_by_medicine(
        session=db_session,
        user_id=user.id,
        local_date=date.today(),
        timezone_name="UTC",
    )
    assert status_map[medicine.id] == "taken"


def test_status_to_emoji_mapping():
    assert IntakeService.status_to_emoji("taken") == "✅"
    assert IntakeService.status_to_emoji("skipped") == "❌"
    assert IntakeService.status_to_emoji("missed") == "⏭️"
    assert IntakeService.status_to_emoji("unknown") == "❔"
