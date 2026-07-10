import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api.dependencies import get_current_user, get_session
from app.api.main import app
from app.api.schemas import FeedbackCreate
from app.database.models import Feedback, User
from app.services.feedback_service import create_feedback, format_feedback_text


def test_feedback_schema_requires_kind_specific_fields():
    with pytest.raises(ValidationError):
        FeedbackCreate(kind="rating")
    with pytest.raises(ValidationError):
        FeedbackCreate(kind="bug", message="   ")


@pytest.mark.asyncio
async def test_feedback_is_persisted_with_diagnostic_context(db_session):
    user = User(telegram_id=42001, username="reporter")
    db_session.add(user)
    await db_session.flush()

    feedback = await create_feedback(
        db_session,
        user,
        kind="bug",
        rating=None,
        message="The save button did not respond",
        diagnostic_context="Page: /settings\nLanguage: en",
        image_bytes=None,
        image_extension=None,
    )

    assert feedback.id is not None
    assert feedback.user_id == user.id
    assert "MedAlarm bug report" in format_feedback_text(feedback, user)
    assert "Page: /settings" in format_feedback_text(feedback, user)


@pytest.mark.asyncio
async def test_feedback_endpoint_accepts_authenticated_multipart(db_session, monkeypatch):
    user = User(telegram_id=42002, username="api_reporter")
    db_session.add(user)
    await db_session.flush()

    async def override_session():
        yield db_session

    async def override_user():
        return user

    async def skip_notification(*args, **kwargs):
        return None

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_user
    monkeypatch.setattr("app.api.routes.notify_feedback", skip_notification)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/feedback",
                data={
                    "kind": "rating",
                    "rating": "5",
                    "message": "Clear and useful",
                    "diagnostic_context": "Page: /settings/feedback",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    feedback = await db_session.get(Feedback, response.json()["id"])
    assert feedback is not None
    assert feedback.rating == 5
    assert feedback.message == "Clear and useful"
