from datetime import UTC, datetime

import pytest

from app.database.models import Medicine, MedicineSchedule, ReminderDispatchLog, User
from app.services.dispatch_recovery_service import DispatchRecoveryService


@pytest.mark.asyncio
async def test_uncertain_dispatch_requires_explicit_audited_recovery(db_session):
    user = User(telegram_id=8100000001)
    db_session.add(user)
    await db_session.flush()
    medicine = Medicine(user_id=user.id, name="Test", dosage_text="1")
    db_session.add(medicine)
    await db_session.flush()
    schedule = MedicineSchedule(medicine_id=medicine.id, time="09:00")
    db_session.add(schedule)
    await db_session.flush()
    sent = ReminderDispatchLog(
        event_id="uncertain-sent",
        medicine_id=medicine.id,
        schedule_id=schedule.id,
        scheduled_ts=100,
        status="uncertain",
        attempt_count=1,
        last_error="transport outcome unknown",
    )
    failed = ReminderDispatchLog(
        event_id="uncertain-failed",
        medicine_id=medicine.id,
        schedule_id=schedule.id,
        scheduled_ts=200,
        status="uncertain",
        attempt_count=1,
    )
    db_session.add_all([sent, failed])
    await db_session.flush()

    uncertain = await DispatchRecoveryService.list_uncertain(db_session)
    assert {row.event_id for row in uncertain} == {"uncertain-sent", "uncertain-failed"}

    recovered_at = datetime(2026, 7, 22, 12, 0, tzinfo=UTC)
    recovered_sent = await DispatchRecoveryService.resolve(
        db_session,
        event_id="uncertain-sent",
        action="confirmed_sent",
        message_id=321,
        note="Verified in the Telegram chat",
        now=recovered_at,
    )
    assert recovered_sent.status == "sent"
    assert recovered_sent.message_id == 321
    assert recovered_sent.recovery_action == "confirmed_sent"
    assert recovered_sent.recovery_note == "Verified in the Telegram chat"
    assert recovered_sent.recovered_at == recovered_at

    recovered_failed = await DispatchRecoveryService.resolve(
        db_session,
        event_id="uncertain-failed",
        action="confirmed_failed",
        note="Verified that no message exists",
        now=recovered_at,
    )
    assert recovered_failed.status == "failed"
    assert recovered_failed.recovery_action == "confirmed_failed"

    assert await DispatchRecoveryService.list_uncertain(db_session) == []
    with pytest.raises(RuntimeError, match="not uncertain"):
        await DispatchRecoveryService.resolve(
            db_session,
            event_id="uncertain-sent",
            action="confirmed_sent",
            message_id=321,
            note="Duplicate recovery",
        )


@pytest.mark.asyncio
async def test_confirmed_delivery_requires_message_id_and_note(db_session):
    with pytest.raises(ValueError, match="message_id"):
        await DispatchRecoveryService.resolve(
            db_session,
            event_id="missing",
            action="confirmed_sent",
            note="Checked",
        )
    with pytest.raises(ValueError, match="note"):
        await DispatchRecoveryService.resolve(
            db_session,
            event_id="missing",
            action="confirmed_failed",
            note=" ",
        )
