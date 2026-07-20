import pytest
from pydantic import ValidationError

from app.api.schemas import MedicineCatalogSnapshot, ReminderConfigPatch, SchedulePayload


def test_schedule_rejects_impossible_time():
    with pytest.raises(ValidationError, match="valid 24-hour time"):
        SchedulePayload(time="24:30")


def test_catalog_snapshot_accepts_long_official_composition():
    snapshot = MedicineCatalogSnapshot(
        source="moh_state_register",
        source_id="record-1",
        trade_name="Official name",
        active_ingredients="x" * 7000,
    )
    assert len(snapshot.active_ingredients or "") == 7000


def test_reminder_config_rejects_ui_only_settings():
    assert ReminderConfigPatch(timezone="Europe/Kyiv").timezone == "Europe/Kyiv"
    with pytest.raises(ValidationError):
        ReminderConfigPatch(text_size="large")


def test_schedule_rejects_invalid_weekday():
    with pytest.raises(ValidationError, match="days_of_week"):
        SchedulePayload(time="08:30", days_of_week="0,7")
