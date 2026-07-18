from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.database.models import IntakeLog, Medicine, MedicineSchedule, User
from app.services.intake_service import IntakeService
from app.services.user_service import UserService


@dataclass(slots=True)
class MedicineCreatePayload:
    name: str
    dosage_text: str
    times: list[str]
    days_of_week: str
    remind_until_confirmed: bool
    snooze_minutes: int
    comment: str | None = None


async def create_medicine_with_schedule(db_session, user: User, payload: MedicineCreatePayload) -> Medicine:
    medicine = Medicine(
        user_id=user.id,
        name=payload.name,
        dosage_text=payload.dosage_text,
        comment=payload.comment,
        is_active=True,
    )
    medicine.schedules = [
        MedicineSchedule(
            time=schedule_time,
            days_of_week=payload.days_of_week,
            snooze_minutes=payload.snooze_minutes,
            remind_until_confirmed=payload.remind_until_confirmed,
        )
        for schedule_time in payload.times
    ]
    db_session.add(medicine)
    await db_session.flush()
    return medicine


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
    medicine = await create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    schedule_id = await db_session.scalar(
        select(MedicineSchedule.id).where(MedicineSchedule.medicine_id == medicine.id)
    )
    assert schedule_id is not None
    within_week = datetime.now(UTC) - timedelta(minutes=1)
    out_of_month = datetime.now(UTC) - timedelta(days=40)
    recent_dispatch = await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(within_week.timestamp()),
    )
    old_dispatch = await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(out_of_month.timestamp()),
    )
    db_session.add_all(
        [
            IntakeLog(
                medicine_id=medicine.id,
                reminder_event_id=recent_dispatch.id,
                scheduled_at=within_week,
                responded_at=within_week,
                status="taken",
            ),
            IntakeLog(
                medicine_id=medicine.id,
                reminder_event_id=old_dispatch.id,
                scheduled_at=out_of_month,
                responded_at=out_of_month,
                status="skipped",
            ),
        ]
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
        times=["08:00"],
        days_of_week="*",
        remind_until_confirmed=True,
        snooze_minutes=10,
    )
    medicine = await create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    await IntakeService.log_intake(
        db_session,
        medicine_id=medicine.id,
        scheduled_at=datetime.now(UTC),
        status="taken",
    )
    await db_session.commit()

    await db_session.delete(medicine)
    await db_session.commit()

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
    medicine = await create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    schedule_id = await db_session.scalar(
        select(MedicineSchedule.id).where(MedicineSchedule.medicine_id == medicine.id)
    )
    assert schedule_id is not None
    now = datetime.now(UTC)
    first = now - timedelta(hours=2)
    second = now - timedelta(hours=1)
    first_dispatch = await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(first.timestamp()),
    )
    second_dispatch = await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(second.timestamp()),
    )
    db_session.add_all(
        [
            IntakeLog(
                medicine_id=medicine.id,
                reminder_event_id=first_dispatch.id,
                scheduled_at=first,
                responded_at=first,
                status="skipped",
            ),
            IntakeLog(
                medicine_id=medicine.id,
                reminder_event_id=second_dispatch.id,
                scheduled_at=second,
                responded_at=second,
                status="taken",
            ),
        ]
    )
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
    medicine = await create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    schedule_id = await db_session.scalar(
        select(MedicineSchedule.id).where(MedicineSchedule.medicine_id == medicine.id)
    )
    assert schedule_id is not None
    now = datetime.now(UTC)
    # A matching medicine/timestamp is not enough: only an intake explicitly
    # linked to this dispatch is a real reminder response.
    await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(now.timestamp()),
    )
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
    medicine = await create_medicine_with_schedule(db_session, user, payload)
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
    medicine = await create_medicine_with_schedule(db_session, user, payload)
    await db_session.flush()
    schedule_id = await db_session.scalar(
        select(MedicineSchedule.id).where(MedicineSchedule.medicine_id == medicine.id)
    )
    assert schedule_id is not None

    older = datetime.now(UTC) - timedelta(hours=2)
    newer = datetime.now(UTC) - timedelta(hours=1)
    older_dispatch = await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(older.timestamp()),
    )
    newer_dispatch = await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule_id,
        scheduled_ts=int(newer.timestamp()),
    )
    db_session.add_all(
        [
            IntakeLog(
                medicine_id=medicine.id,
                reminder_event_id=older_dispatch.id,
                scheduled_at=older,
                responded_at=newer,
                status="taken",
            ),
            IntakeLog(
                medicine_id=medicine.id,
                reminder_event_id=newer_dispatch.id,
                scheduled_at=newer,
                responded_at=older,
                status="skipped",
            ),
        ]
    )
    await db_session.commit()

    history = await IntakeService.history(db_session, user.id, period="today")
    assert len(history) == 2
    assert history[0].status == "taken"
    assert history[0].responded_at >= history[1].responded_at


@pytest.mark.asyncio
async def test_dispatch_lookup_can_be_scoped_to_owning_user(db_session):
    owner = User(telegram_id=88001, timezone="UTC")
    other = User(telegram_id=88002, timezone="UTC")
    db_session.add_all([owner, other])
    await db_session.flush()
    medicine = Medicine(user_id=owner.id, name="D3", dosage_text="1", is_active=True)
    db_session.add(medicine)
    await db_session.flush()
    schedule = MedicineSchedule(medicine_id=medicine.id, time="10:00", days_of_week="*")
    db_session.add(schedule)
    await db_session.flush()
    scheduled_ts = int(datetime.now(UTC).timestamp())
    await IntakeService.log_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule.id,
        scheduled_ts=scheduled_ts,
    )

    own = await IntakeService.get_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule.id,
        scheduled_ts=scheduled_ts,
        user_id=owner.id,
    )
    unauthorized = await IntakeService.get_dispatch(
        db_session,
        medicine_id=medicine.id,
        schedule_id=schedule.id,
        scheduled_ts=scheduled_ts,
        user_id=other.id,
    )

    assert own is not None
    assert unauthorized is None


def test_status_to_emoji_mapping():
    assert IntakeService.status_to_emoji("taken") == "✅"
    assert IntakeService.status_to_emoji("skipped") == "❌"
    assert IntakeService.status_to_emoji("missed") == "⏭️"
    assert IntakeService.status_to_emoji("unknown") == "❔"
