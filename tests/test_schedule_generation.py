from datetime import UTC, datetime

import pytest

from app.database.models import User
from app.services.medicine_sync_service import MedicineSyncPayload, MedicineSyncService, ScheduleSyncPayload
from app.services.schedule_service import ScheduleService
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_schedule_generation_tracks_sync_and_timezone_changes(db_session):
    user = User(telegram_id=8000000001, timezone="UTC")
    db_session.add(user)
    await db_session.flush()

    assert await ScheduleService.generation(db_session) == 0

    applied, _ = await MedicineSyncService.apply(
        db_session,
        user,
        MedicineSyncPayload(
            client_medicine_id="generation-test",
            name="Test",
            dosage_text="1",
            comment=None,
            is_active=True,
            updated_at=datetime(2026, 7, 22, 12, 0, tzinfo=UTC),
            deleted_at=None,
            schedules=[ScheduleSyncPayload(time="09:00")],
        ),
    )
    assert applied is True
    assert await ScheduleService.generation(db_session) == 1

    await UserService.update_timezone(db_session, user.telegram_id, "Europe/Kyiv")
    assert await ScheduleService.generation(db_session) == 2

    # Replaying the same timezone projection must not cause needless reloads.
    await UserService.update_timezone(db_session, user.telegram_id, "Europe/Kyiv")
    assert await ScheduleService.generation(db_session) == 2
