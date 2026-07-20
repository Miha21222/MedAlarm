from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.dependencies import get_current_user, get_session
from app.api.main import app
from app.database.models import Medicine, MedicineSchedule, User
from app.services.intake_service import IntakeService


async def _authenticated_client(db_session, user: User) -> AsyncClient:
    async def override_session():
        yield db_session

    async def override_user():
        return user

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_user
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_settings_routes_patch_and_validate(db_session):
    user = User(telegram_id=51001, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    medicine = Medicine(user_id=user.id, name="Existing", dosage_text="1")
    medicine.schedules = [
        MedicineSchedule(time="09:00", days_of_week="*", snooze_minutes=10)
    ]
    db_session.add(medicine)
    await db_session.flush()
    client = await _authenticated_client(db_session, user)
    try:
        current = await client.get("/api/v1/settings/me")
        updated = await client.patch(
            "/api/v1/settings/me",
            json={"language": "uk", "text_size": "large", "default_snooze_minutes": 20},
        )
        invalid = await client.patch("/api/v1/settings/me", json={"timezone": "Not/A_Zone"})
    finally:
        await client.aclose()
        app.dependency_overrides.clear()

    assert current.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["language"] == "uk"
    assert updated.json()["text_size"] == "large"
    assert user.default_snooze_minutes == 20
    assert medicine.schedules[0].snooze_minutes == 20
    assert invalid.status_code == 422


@pytest.mark.asyncio
async def test_medicine_sync_bootstrap_and_id_validation(db_session):
    user = User(telegram_id=51002, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    client = await _authenticated_client(db_session, user)
    payload = {
        "client_medicine_id": "http-test-medicine",
        "name": "Vitamin D",
        "dosage_text": "1 capsule",
        "comment": None,
        "is_active": True,
        "created_at": "2026-07-18T08:00:00Z",
        "updated_at": "2026-07-18T08:00:00Z",
        "deleted_at": None,
        "schedules": [{"time": "09:00", "days_of_week": "*"}],
    }
    try:
        mismatch = await client.put("/api/v1/sync/medicines/other-id", json=payload)
        synced = await client.put("/api/v1/sync/medicines/http-test-medicine", json=payload)
        bootstrap = await client.get("/api/v1/sync/bootstrap")
        batch = await client.post("/api/v1/sync/batch", json={"medicines": [payload]})
    finally:
        await client.aclose()
        app.dependency_overrides.clear()

    assert mismatch.status_code == 400
    assert synced.status_code == 200
    assert synced.json()["applied"] is True
    assert bootstrap.status_code == 200
    assert bootstrap.json()["medicines"][0]["client_medicine_id"] == "http-test-medicine"
    assert batch.status_code == 200
    assert batch.json()["items"][0]["applied"] is False


@pytest.mark.asyncio
async def test_dashboard_reminder_action_history_and_adherence_routes(db_session):
    user = User(telegram_id=51003, timezone="UTC")
    db_session.add(user)
    await db_session.flush()
    client = await _authenticated_client(db_session, user)
    now = datetime.now(UTC)
    payload = {
        "client_medicine_id": "actionable-medicine",
        "name": "Magnesium",
        "dosage_text": "1 tablet",
        "comment": None,
        "is_active": True,
        "created_at": (now - timedelta(minutes=1)).isoformat(),
        "updated_at": now.isoformat(),
        "deleted_at": None,
        "schedules": [{"time": now.strftime("%H:%M"), "days_of_week": "*"}],
    }
    try:
        synced = await client.put("/api/v1/sync/medicines/actionable-medicine", json=payload)
        synced_medicine = synced.json()["medicine"]
        medicine = await db_session.scalar(
            select(Medicine).where(Medicine.client_medicine_id == synced_medicine["client_medicine_id"])
        )
        assert medicine is not None
        schedule = await db_session.scalar(select(MedicineSchedule).where(MedicineSchedule.medicine_id == medicine.id))
        assert schedule is not None
        dispatch = await IntakeService.log_dispatch(
            db_session,
            medicine_id=medicine.id,
            schedule_id=schedule.id,
            scheduled_ts=int(now.replace(second=0, microsecond=0).timestamp()),
        )
        await db_session.flush()

        dashboard = await client.get("/api/v1/dashboard/today")
        action = await client.post(
            f"/api/v1/reminder-events/{dispatch.event_id}/actions",
            json={"action": "taken"},
        )
        repeated = await client.post(
            f"/api/v1/reminder-events/{dispatch.event_id}/actions",
            json={"action": "taken"},
        )
        history = await client.get("/api/v1/history?period=today")
        adherence = await client.get("/api/v1/dashboard/adherence?period=7d")
        missing = await client.post("/api/v1/reminder-events/missing/actions", json={"action": "taken"})
    finally:
        await client.aclose()
        app.dependency_overrides.clear()

    assert dashboard.status_code == 200
    assert any(item["event_id"] == dispatch.event_id for item in dashboard.json()["items"])
    assert action.status_code == 200
    assert action.json()["status"] == "taken"
    assert repeated.status_code == 200
    assert repeated.json()["intake_id"] == action.json()["intake_id"]
    assert history.status_code == 200
    assert history.json()["items"][0]["event_id"] == dispatch.event_id
    assert adherence.status_code == 200
    assert adherence.json()["counts"]["taken"] == 1
    assert missing.status_code == 404
