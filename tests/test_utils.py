from datetime import UTC, datetime

import pytest

from app.utils.datetime_utils import (
    is_schedule_available_on_creation_day,
    normalize_time_string,
    parse_days_input,
    parse_times_input,
    period_range,
)


def test_normalize_time_string():
    assert normalize_time_string("9:5") == "09:05"
    assert normalize_time_string("23:59") == "23:59"


def test_parse_times_input():
    assert parse_times_input("21:00, 09:00,9:0") == ["09:00", "21:00"]


def test_parse_days_input_numeric():
    assert parse_days_input("1,3,5") == [0, 2, 4]


def test_parse_days_input_aliases():
    assert parse_days_input("пн,ср,вс") == [0, 2, 6]


def test_parse_days_input_invalid():
    with pytest.raises(ValueError):
        parse_days_input("понедельник")


def test_schedule_availability_on_creation_day_uses_local_time():
    created_at = datetime(2026, 7, 7, 12, 0, 30, tzinfo=UTC)  # 15:00 in Kyiv

    assert not is_schedule_available_on_creation_day(created_at, "09:00", created_at.date(), "UTC")
    assert is_schedule_available_on_creation_day(created_at, "12:00", created_at.date(), "UTC")
    assert is_schedule_available_on_creation_day(created_at, "16:00", datetime(2026, 7, 7).date(), "Europe/Kyiv")
    assert is_schedule_available_on_creation_day(created_at, "09:00", datetime(2026, 7, 8).date(), "Europe/Kyiv")


def test_period_range_today_uses_user_calendar_day():
    start, end = period_range("today", datetime(2026, 7, 7, 22, 30, tzinfo=UTC), "Europe/Kyiv")

    assert start == datetime(2026, 7, 7, 21, 0, tzinfo=UTC)
    assert end == datetime(2026, 7, 8, 21, 0, tzinfo=UTC)


def test_period_range_week_and_month_use_user_calendar_boundaries():
    now = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)

    week_start, week_end = period_range("week", now, "Europe/Kyiv")
    month_start, month_end = period_range("month", now, "Europe/Kyiv")

    assert week_start == datetime(2026, 7, 5, 21, 0, tzinfo=UTC)
    assert week_end == datetime(2026, 7, 12, 21, 0, tzinfo=UTC)
    assert month_start == datetime(2026, 6, 30, 21, 0, tzinfo=UTC)
    assert month_end == datetime(2026, 7, 31, 21, 0, tzinfo=UTC)
