from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

WEEKDAY_LABELS = {
    0: "Пн",
    1: "Вт",
    2: "Ср",
    3: "Чт",
    4: "Пт",
    5: "Сб",
    6: "Вс",
}

WEEKDAY_ALIASES = {
    "1": 0,
    "2": 1,
    "3": 2,
    "4": 3,
    "5": 4,
    "6": 5,
    "7": 6,
    "пн": 0,
    "вт": 1,
    "ср": 2,
    "чт": 3,
    "пт": 4,
    "сб": 5,
    "вс": 6,
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}


def validate_timezone(timezone_name: str) -> bool:
    try:
        ZoneInfo(timezone_name)
        return True
    except ZoneInfoNotFoundError:
        return False


def parse_time_string(time_string: str) -> tuple[int, int]:
    try:
        hour_str, minute_str = time_string.strip().split(":")
        hour = int(hour_str)
        minute = int(minute_str)
    except (ValueError, TypeError) as exc:
        raise ValueError("Используйте формат ЧЧ:ММ, например 09:30.") from exc
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError("Часы должны быть в диапазоне 00-23, минуты 00-59.")
    return hour, minute


def normalize_time_string(time_string: str) -> str:
    hour, minute = parse_time_string(time_string)
    return f"{hour:02d}:{minute:02d}"


def parse_times_input(times_input: str) -> list[str]:
    if not times_input:
        raise ValueError("Нужно указать хотя бы одно время.")
    parts = [part.strip() for part in times_input.split(",") if part.strip()]
    if not parts:
        raise ValueError("Нужно указать хотя бы одно время.")
    return sorted({normalize_time_string(part) for part in parts})


def format_times(times: list[str]) -> str:
    return ", ".join(sorted(times))


def parse_days_input(days_input: str) -> list[int]:
    if not days_input:
        raise ValueError("Нужно указать дни недели.")
    parts = [part.strip().lower() for part in days_input.split(",") if part.strip()]
    if not parts:
        raise ValueError("Нужно указать дни недели.")
    days: set[int] = set()
    for part in parts:
        if part not in WEEKDAY_ALIASES:
            raise ValueError("Используйте номера 1-7 или сокращения: пн,вт,ср,чт,пт,сб,вс.")
        days.add(WEEKDAY_ALIASES[part])
    return sorted(days)


def serialize_days(days: list[int]) -> str:
    if not days:
        return "*"
    return ",".join(str(day) for day in sorted(set(days)))


def deserialize_days(serialized_days: str) -> list[int]:
    if not serialized_days or serialized_days == "*":
        return list(range(7))
    return sorted(int(part) for part in serialized_days.split(",") if part)


def format_days(serialized_days: str) -> str:
    if serialized_days == "*":
        return "каждый день"
    return ", ".join(WEEKDAY_LABELS[day] for day in deserialize_days(serialized_days))


def is_due_today(serialized_days: str, target_date: date) -> bool:
    if serialized_days == "*":
        return True
    return target_date.weekday() in deserialize_days(serialized_days)


def is_schedule_available_on_creation_day(
    created_at: datetime | None,
    schedule_time: str,
    target_date: date,
    timezone_name: str,
) -> bool:
    if created_at is None:
        return True
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    created_local = created_at.astimezone(ZoneInfo(timezone_name))
    if created_local.date() != target_date:
        return True
    hour, minute = parse_time_string(schedule_time)
    return (hour, minute) >= (created_local.hour, created_local.minute)


def utc_now() -> datetime:
    return datetime.now(UTC)


def now_in_timezone(timezone_name: str) -> datetime:
    return utc_now().astimezone(ZoneInfo(timezone_name))


def period_range(period: str, now_utc: datetime, timezone_name: str = "UTC") -> tuple[datetime, datetime | None]:
    local_now = now_utc.astimezone(ZoneInfo(timezone_name))
    start_of_today = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "today":
        start_local = start_of_today
        end_local = start_local + timedelta(days=1)
    elif period == "month":
        start_local = start_of_today.replace(day=1)
        end_local = (
            start_local.replace(year=start_local.year + 1, month=1)
            if start_local.month == 12
            else start_local.replace(month=start_local.month + 1)
        )
    else:
        start_local = start_of_today - timedelta(days=start_of_today.weekday())
        end_local = start_local + timedelta(days=7)
    return start_local.astimezone(UTC), end_local.astimezone(UTC)


def period_start(period: str, now_utc: datetime, timezone_name: str = "UTC") -> datetime:
    return period_range(period, now_utc, timezone_name)[0]
