from __future__ import annotations

from app.scheduler.jobs import ReminderScheduler

_scheduler: ReminderScheduler | None = None


def set_scheduler(scheduler: ReminderScheduler) -> None:
    global _scheduler
    _scheduler = scheduler


def get_scheduler() -> ReminderScheduler | None:
    return _scheduler

