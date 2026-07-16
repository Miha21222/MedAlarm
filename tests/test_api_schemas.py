import pytest
from pydantic import ValidationError

from app.api.schemas import MedicineCatalogSnapshot, SchedulePayload, SettingsPatch


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


def test_settings_accept_only_supported_text_sizes():
    assert SettingsPatch(text_size="large").text_size == "large"
    with pytest.raises(ValidationError):
        SettingsPatch(text_size="huge")


def test_schedule_rejects_invalid_weekday():
    with pytest.raises(ValidationError, match="days_of_week"):
        SchedulePayload(time="08:30", days_of_week="0,7")
