import pytest
from pydantic import ValidationError

from app.api.schemas import SchedulePayload


def test_schedule_rejects_impossible_time():
    with pytest.raises(ValidationError, match="valid 24-hour time"):
        SchedulePayload(time="24:30")


def test_schedule_rejects_invalid_weekday():
    with pytest.raises(ValidationError, match="days_of_week"):
        SchedulePayload(time="08:30", days_of_week="0,7")
