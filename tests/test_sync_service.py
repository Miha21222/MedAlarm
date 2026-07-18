from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.routes import dashboard_today
from app.database.models import IntakeLog, Medicine, MedicineSchedule, ReminderDispatchLog, User
from app.services.intake_service import IntakeService
from app.services.medicine_sync_service import MedicineSyncPayload, MedicineSyncService, ScheduleSyncPayload
from app.services.reminder_action_service import ReminderActionService


@pytest.mark.asyncio
async def test_newer_medicine_aggregate_replaces_schedules(db_session):
    user = User(telegram_id=8101, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    older = datetime.now(UTC) - timedelta(minutes=5)
    newer = datetime.now(UTC)

    await MedicineSyncService.apply(
        db_session,
        user,
        MedicineSyncPayload(
            client_medicine_id="med-sync-1",
            name="Old",
            dosage_text="1",
            comment=None,
            is_active=True,
            updated_at=older,
            deleted_at=None,
            schedules=[ScheduleSyncPayload(time="08:00", days_of_week="*")],
        ),
    )
    applied, medicine = await MedicineSyncService.apply(
        db_session,
        user,
        MedicineSyncPayload(
            client_medicine_id="med-sync-1",
            name="New",
            dosage_text="2",
            comment="after food",
            catalog={
                "source": "moh_state_register",
                "source_id": "record-1",
                "trade_name": "New",
                "registration_number": "UA/1/01/01",
            },
            is_active=True,
            updated_at=newer,
            deleted_at=None,
            schedules=[
                ScheduleSyncPayload(time="07:30", days_of_week="0,2,4"),
                ScheduleSyncPayload(time="20:00", days_of_week="*"),
            ],
        ),
    )
    await db_session.commit()

    stored = await db_session.scalar(
        select(Medicine)
        .where(Medicine.id == medicine.id)
        .options(selectinload(Medicine.schedules))
    )
    assert applied is True
    assert stored is not None
    assert stored.name == "New"
    assert stored.catalog_snapshot["registration_number"] == "UA/1/01/01"
    assert [slot.time for slot in stored.schedules] == ["07:30", "20:00"]


@pytest.mark.asyncio
async def test_sync_reuses_unchanged_schedule_without_unique_constraint_failure(db_session):
    user = User(telegram_id=8107, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    older = datetime.now(UTC) - timedelta(minutes=1)
    payload = MedicineSyncPayload(
        client_medicine_id="stable-slot",
        name="Medicine",
        dosage_text="1",
        comment=None,
        is_active=True,
        updated_at=older,
        deleted_at=None,
        schedules=[ScheduleSyncPayload(time="18:10", days_of_week="*")],
    )
    _, medicine = await MedicineSyncService.apply(db_session, user, payload)
    await db_session.commit()
    original_schedule_id = medicine.schedules[0].id

    applied, medicine = await MedicineSyncService.apply(
        db_session,
        user,
        replace(
            payload,
            updated_at=older + timedelta(minutes=1),
            schedules=[
                ScheduleSyncPayload(time="18:10", days_of_week="*", snooze_minutes=15),
                ScheduleSyncPayload(time="18:10", days_of_week="*", snooze_minutes=20),
            ],
        ),
    )
    await db_session.commit()

    assert applied is True
    assert len(medicine.schedules) == 1
    assert medicine.schedules[0].id == original_schedule_id
    assert medicine.schedules[0].snooze_minutes == 20


@pytest.mark.asyncio
async def test_schedule_change_preserves_linked_reminder_history(db_session):
    user = User(telegram_id=8108, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    older = datetime.now(UTC) - timedelta(minutes=1)
    payload = MedicineSyncPayload(
        client_medicine_id="historical-slot",
        name="Medicine",
        dosage_text="1",
        comment=None,
        is_active=True,
        updated_at=older,
        deleted_at=None,
        schedules=[ScheduleSyncPayload(time="08:00", days_of_week="*")],
    )
    _, medicine = await MedicineSyncService.apply(db_session, user, payload)
    dispatch = ReminderDispatchLog(
        event_id="evt-before-schedule-edit",
        medicine_id=medicine.id,
        schedule_id=medicine.schedules[0].id,
        scheduled_ts=int(older.timestamp()),
        status="taken",
        resolved_at=older,
    )
    db_session.add(dispatch)
    await db_session.flush()
    intake = IntakeLog(
        medicine_id=medicine.id,
        reminder_event_id=dispatch.id,
        scheduled_at=older,
        responded_at=older,
        status="taken",
    )
    db_session.add(intake)
    await db_session.commit()
    dispatch_db_id = dispatch.id

    await MedicineSyncService.apply(
        db_session,
        user,
        replace(
            payload,
            updated_at=older + timedelta(minutes=1),
            schedules=[ScheduleSyncPayload(time="09:00", days_of_week="*")],
        ),
    )
    await db_session.commit()
    db_session.expire_all()

    stored_dispatch = await db_session.scalar(
        select(ReminderDispatchLog).where(ReminderDispatchLog.event_id == "evt-before-schedule-edit")
    )
    stored_intake = await db_session.scalar(
        select(IntakeLog).where(IntakeLog.reminder_event_id == dispatch_db_id)
    )
    assert stored_dispatch is not None
    assert stored_dispatch.schedule_id is None
    assert stored_intake is not None


@pytest.mark.asyncio
async def test_older_medicine_aggregate_is_ignored(db_session):
    user = User(telegram_id=8102, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    newer = datetime.now(UTC)
    payload = MedicineSyncPayload(
        client_medicine_id="med-sync-2",
        name="Current",
        dosage_text="1",
        comment=None,
        is_active=True,
        updated_at=newer,
        deleted_at=None,
        schedules=[],
    )
    await MedicineSyncService.apply(db_session, user, payload)
    applied, medicine = await MedicineSyncService.apply(
        db_session,
        user,
        replace(payload, name="Stale", updated_at=newer - timedelta(minutes=1)),
    )
    assert applied is False
    assert medicine.name == "Current"


@pytest.mark.asyncio
async def test_manual_and_catalogue_medicines_share_sync_and_dashboard_rules(db_session):
    user = User(telegram_id=8105, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    now = datetime.now(UTC)
    manual_payload = MedicineSyncPayload(
        client_medicine_id="manual-parity",
        name="Manual medicine",
        dosage_text="1 tablet",
        comment="same user-entered instructions",
        is_active=True,
        created_at=now - timedelta(days=1),
        updated_at=now,
        deleted_at=None,
        schedules=[ScheduleSyncPayload(time="16:00", days_of_week="*")],
    )
    _, manual = await MedicineSyncService.apply(db_session, user, manual_payload)
    _, catalogue = await MedicineSyncService.apply(
        db_session,
        user,
        replace(
            manual_payload,
            client_medicine_id="catalogue-parity",
            name="Catalogue medicine",
            catalog={"source": "moh_state_register", "source_id": "record-1", "trade_name": "Catalogue medicine"},
        ),
    )

    doses = await IntakeService.today_doses(db_session, user.id, now.date(), "UTC")
    doses_by_medicine = {dose.medicine.client_medicine_id: dose for dose in doses}

    assert manual.catalog_snapshot is None
    assert catalogue.catalog_snapshot is not None
    assert set(doses_by_medicine) == {"manual-parity", "catalogue-parity"}
    assert doses_by_medicine["manual-parity"].schedule.time == doses_by_medicine["catalogue-parity"].schedule.time
    assert doses_by_medicine["manual-parity"].status == doses_by_medicine["catalogue-parity"].status == "pending"
    assert doses_by_medicine["manual-parity"].actionable is doses_by_medicine["catalogue-parity"].actionable is False


@pytest.mark.asyncio
async def test_dashboard_today_serializes_schedules_after_fresh_database_load(db_session):
    user = User(telegram_id=8106, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    now = datetime.now(UTC)
    await MedicineSyncService.apply(
        db_session,
        user,
        MedicineSyncPayload(
            client_medicine_id="dashboard-prod",
            name="Dashboard medicine",
            dosage_text="1",
            comment=None,
            is_active=True,
            created_at=now - timedelta(days=1),
            updated_at=now,
            deleted_at=None,
            schedules=[ScheduleSyncPayload(time="16:00", days_of_week="*")],
        ),
    )
    await db_session.commit()
    db_session.expunge_all()
    fresh_user = await db_session.scalar(select(User).where(User.telegram_id == 8106))
    assert fresh_user is not None

    payload = await dashboard_today(user=fresh_user, session=db_session)

    assert len(payload["items"]) == 1
    assert payload["items"][0]["schedules"][0]["time"] == "16:00"


@pytest.mark.asyncio
async def test_reminder_action_is_idempotent(db_session):
    user = User(telegram_id=8103, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    medicine = Medicine(user_id=user.id, name="D3", dosage_text="1")
    db_session.add(medicine)
    await db_session.flush()
    event = ReminderDispatchLog(
        event_id="evt-idempotent",
        medicine_id=medicine.id,
        scheduled_ts=int(datetime.now(UTC).timestamp()),
        status="sent",
    )
    db_session.add(event)
    await db_session.flush()

    first = await ReminderActionService.resolve(db_session, user.id, "evt-idempotent", "taken")
    second = await ReminderActionService.resolve(db_session, user.id, "evt-idempotent", "taken")
    await db_session.commit()

    assert first.intake_id == second.intake_id
    assert second.status == "taken"


@pytest.mark.asyncio
async def test_today_doses_keeps_multiple_schedule_slots_independent(db_session):
    user = User(telegram_id=8104, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    medicine = Medicine(
        user_id=user.id,
        name="D3",
        dosage_text="1",
        created_at=datetime.now(UTC) - timedelta(days=1),
    )
    medicine.schedules = [
        MedicineSchedule(time="08:00", days_of_week="*"),
        MedicineSchedule(time="20:00", days_of_week="*"),
    ]
    db_session.add(medicine)
    await db_session.flush()
    now = datetime.now(UTC)
    dispatch = ReminderDispatchLog(
        event_id="evt-morning",
        medicine_id=medicine.id,
        schedule_id=medicine.schedules[0].id,
        scheduled_ts=int(now.timestamp()),
        status="taken",
        resolved_at=now,
    )
    db_session.add(dispatch)
    await db_session.flush()
    db_session.add(
        IntakeLog(
            medicine_id=medicine.id,
            reminder_event_id=dispatch.id,
            scheduled_at=now,
            responded_at=now,
            status="taken",
        )
    )
    await db_session.flush()

    doses = await IntakeService.today_doses(db_session, user.id, now.date(), "UTC")

    assert [dose.schedule.time for dose in doses] == ["08:00", "20:00"]
    assert doses[0].status == "taken"
    assert doses[0].event_id == "evt-morning"
    assert doses[0].actionable is False
    assert doses[1].status == "pending"
    assert doses[1].event_id is None
    assert doses[1].actionable is False
