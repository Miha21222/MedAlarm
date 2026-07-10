from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

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
    assert [slot.time for slot in stored.schedules] == ["07:30", "20:00"]


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
    medicine = Medicine(user_id=user.id, name="D3", dosage_text="1")
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
