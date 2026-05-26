import pytest

from app.utils.datetime_utils import normalize_time_string, parse_days_input


def test_normalize_time_string():
    assert normalize_time_string("9:5") == "09:05"
    assert normalize_time_string("23:59") == "23:59"


def test_parse_days_input_numeric():
    assert parse_days_input("1,3,5") == [0, 2, 4]


def test_parse_days_input_aliases():
    assert parse_days_input("пн,ср,вс") == [0, 2, 6]


def test_parse_days_input_invalid():
    with pytest.raises(ValueError):
        parse_days_input("понедельник")

