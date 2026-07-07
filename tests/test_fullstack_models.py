from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.models import (
    IntakeLog,
    Medicine,
    ReminderDispatchLog,
    User,
)


@pytest.mark.asyncio
async def test_medicine_has_stable_client_id_and_sync_timestamps(db_session):
    user = User(telegram_id=7001, timezone="UTC")
    db_session.add(user)
    await db_session.flush()

    medicine = Medicine(
        user_id=user.id,
        client_medicine_id="med-client-1",
        name="Vitamin D",
        dosage_text="1 capsule",
        updated_at=datetime.now(UTC),
    )
    db_session.add(medicine)
    await db_session.commit()

    stored = await db_session.scalar(
        select(Medicine).where(Medicine.client_medicine_id == "med-client-1")
    )
    assert stored is not None
    assert stored.deleted_at is None


@pytest.mark.asyncio
async def test_one_intake_result_is_allowed_per_reminder_event(db_session):
    user = User(telegram_id=7002, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    medicine = Medicine(
        user_id=user.id,
        client_medicine_id="med-client-2",
        name="Magnesium",
        dosage_text="1 tablet",
        updated_at=datetime.now(UTC),
    )
    db_session.add(medicine)
    await db_session.flush()
    dispatch = ReminderDispatchLog(
        event_id="event-1",
        medicine_id=medicine.id,
        schedule_id=None,
        scheduled_ts=int(datetime.now(UTC).timestamp()),
        status="sent",
    )
    db_session.add(dispatch)
    await db_session.flush()
    db_session.add_all(
        [
            IntakeLog(
                medicine_id=medicine.id,
                reminder_event_id=dispatch.id,
                scheduled_at=datetime.now(UTC),
                status="taken",
                responded_at=datetime.now(UTC),
            ),
            IntakeLog(
                medicine_id=medicine.id,
                reminder_event_id=dispatch.id,
                scheduled_at=datetime.now(UTC),
                status="skipped",
                responded_at=datetime.now(UTC),
            ),
        ]
    )

    with pytest.raises(IntegrityError):
        await db_session.commit()
