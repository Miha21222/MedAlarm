from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.database.models import IntakeLog, Medicine, MedicineSchedule, User
from app.services.intake_service import IntakeService
from app.services.medicine_service import MedicineCreatePayload, MedicineService
from app.services.schedule_service import ScheduleService
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
        times=["09:00", "21:00"],
        days_of_week="*",
        remind_until_confirmed=True,
        snooze_minutes=10,
    )
    medicine = await MedicineService.create_medicine_with_schedule(db_session, user, payload)
    await db_session.commit()
    meds = await MedicineService.list_active_medicines(db_session, user.id)
    assert len(meds) == 1
    assert meds[0].id == medicine.id
    assert [schedule.time for schedule in meds[0].schedules] == ["09:00", "21:00"]


@pytest.mark.asyncio
async def test_update_medicine_replaces_schedules(db_session):
    user = User(telegram_id=11223, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    created_payload = MedicineCreatePayload(
        name="Омега-3",
        dosage_text="1 капсула",
        times=["08:00", "20:00"],
        days_of_week="*",
        remind_until_confirmed=True,
        snooze_minutes=10,
    )
    medicine = await MedicineService.create_medicine_with_schedule(db_session, user, created_payload)
    await db_session.flush()
    updated_payload = MedicineCreatePayload(
        name="Омега-3 New",
        dosage_text="2 капсулы",
        times=["07:30", "13:00", "22:15"],
        days_of_week="*",
        remind_until_confirmed=False,
        snooze_minutes=15,
    )
    await MedicineService.update_medicine_with_schedule(db_session, medicine, updated_payload)
    await db_session.commit()

    updated = await MedicineService.get_user_medicine(db_session, medicine.id, user.id)
    assert updated is not None
    assert updated.name == "Омега-3 New"
    assert updated.dosage_text == "2 капсулы"
    assert [schedule.time for schedule in updated.schedules] == ["07:30", "13:00", "22:15"]


@pytest.mark.asyncio
async def test_history_filters_by_period(db_session):
    user = User(telegram_id=7788, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    payload = MedicineCreatePayload(
        name="Омега-3",
        dosage_text="1 капсула",
        times=["09:00"],
        days_of_week="*",
        remind_until_confirmed=True,
        snooze_minutes=10,
    )
    medicine = await MedicineService.create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    schedule_id = await db_session.scalar(
        select(MedicineSchedule.id).where(MedicineSchedule.medicine_id == medicine.id)
    )
    assert schedule_id is not None
    within_week = datetime.now(UTC) - timedelta(minutes=1)
    out_of_month = datetime.now(UTC) - timedelta(days=40)
    await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(within_week.timestamp()),
    )
    await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(out_of_month.timestamp()),
    )
    await IntakeService.log_intake(db_session, medicine.id, within_week, "taken")
    await IntakeService.log_intake(db_session, medicine.id, out_of_month, "skipped")
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
        times=["08:00"],
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
        times=["10:00"],
        days_of_week="*",
        remind_until_confirmed=True,
        snooze_minutes=10,
    )
    medicine = await MedicineService.create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    schedule_id = await db_session.scalar(
        select(MedicineSchedule.id).where(MedicineSchedule.medicine_id == medicine.id)
    )
    assert schedule_id is not None
    now = datetime.now(UTC)
    first = now - timedelta(hours=2)
    second = now - timedelta(hours=1)
    await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(first.timestamp()),
    )
    await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(second.timestamp()),
    )
    await IntakeService.log_intake(db_session, medicine.id, first, "skipped")
    await IntakeService.log_intake(db_session, medicine.id, second, "taken")
    await db_session.commit()

    status_map = await IntakeService.today_status_by_medicine(
        session=db_session,
        user_id=user.id,
        local_date=date.today(),
        timezone_name="UTC",
    )
    assert status_map[medicine.id] == "taken"


@pytest.mark.asyncio
async def test_history_and_today_ignore_intake_without_dispatch(db_session):
    user = User(telegram_id=5555, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    payload = MedicineCreatePayload(
        name="Цинк",
        dosage_text="1 таблетка",
        times=["12:00"],
        days_of_week="*",
        remind_until_confirmed=True,
        snooze_minutes=10,
    )
    medicine = await MedicineService.create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    now = datetime.now(UTC)
    await IntakeService.log_intake(db_session, medicine.id, now, "taken")
    await db_session.commit()

    history = await IntakeService.history(db_session, user.id, period="today")
    status_map = await IntakeService.today_status_by_medicine(
        session=db_session,
        user_id=user.id,
        local_date=date.today(),
        timezone_name="UTC",
    )

    assert history == []
    assert medicine.id not in status_map


@pytest.mark.asyncio
async def test_has_dispatch_checks_event_triplet(db_session):
    user = User(telegram_id=6666, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    payload = MedicineCreatePayload(
        name="Магний",
        dosage_text="1 таблетка",
        times=["18:00"],
        days_of_week="*",
        remind_until_confirmed=True,
        snooze_minutes=10,
    )
    medicine = await MedicineService.create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    schedule_id = await db_session.scalar(
        select(MedicineSchedule.id).where(MedicineSchedule.medicine_id == medicine.id)
    )
    assert schedule_id is not None
    scheduled_ts = int(datetime.now(UTC).timestamp())

    assert await IntakeService.has_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=scheduled_ts,
    ) is False

    await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=scheduled_ts,
    )
    await db_session.commit()

    assert await IntakeService.has_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=scheduled_ts,
    ) is True


@pytest.mark.asyncio
async def test_get_user_today_medicines_sorted_by_time_ascending(db_session):
    user = User(telegram_id=7777, timezone="UTC")
    db_session.add(user)
    await db_session.flush()

    morning = await MedicineService.create_medicine_with_schedule(
        db_session,
        user,
        MedicineCreatePayload(
            name="Утренний",
            dosage_text="1 таблетка",
            times=["08:00"],
            days_of_week="*",
            remind_until_confirmed=True,
            snooze_minutes=10,
        ),
    )
    evening = await MedicineService.create_medicine_with_schedule(
        db_session,
        user,
        MedicineCreatePayload(
            name="Вечерний",
            dosage_text="1 таблетка",
            times=["17:00"],
            days_of_week="*",
            remind_until_confirmed=True,
            snooze_minutes=10,
        ),
    )
    await db_session.commit()

    medicines = await ScheduleService.get_user_today_medicines(db_session, user.id, date.today())
    assert [medicine.id for medicine in medicines] == [morning.id, evening.id]


@pytest.mark.asyncio
async def test_history_sorted_by_newest_first(db_session):
    user = User(telegram_id=8888, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    payload = MedicineCreatePayload(
        name="Тест",
        dosage_text="1 таблетка",
        times=["10:00"],
        days_of_week="*",
        remind_until_confirmed=True,
        snooze_minutes=10,
    )
    medicine = await MedicineService.create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    schedule_id = await db_session.scalar(
        select(MedicineSchedule.id).where(MedicineSchedule.medicine_id == medicine.id)
    )
    assert schedule_id is not None

    older = datetime.now(UTC) - timedelta(hours=2)
    newer = datetime.now(UTC) - timedelta(hours=1)
    await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(older.timestamp()),
    )
    await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(newer.timestamp()),
    )
    await IntakeService.log_intake(db_session, medicine.id, older, "taken")
    await IntakeService.log_intake(db_session, medicine.id, newer, "skipped")
    await db_session.commit()

    history = await IntakeService.history(db_session, user.id, period="today")
    assert len(history) == 2
    assert history[0].scheduled_at >= history[1].scheduled_at


def test_status_to_emoji_mapping():
    assert IntakeService.status_to_emoji("taken") == "✅"
    assert IntakeService.status_to_emoji("skipped") == "❌"
    assert IntakeService.status_to_emoji("missed") == "⏭️"
    assert IntakeService.status_to_emoji("unknown") == "❔"
