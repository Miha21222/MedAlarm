from datetime import UTC, datetime, timedelta

from app.database.models import MedicineSchedule
from app.scheduler.jobs import ReminderScheduler


def test_scheduler_creates_daily_job():
    scheduler = ReminderScheduler()
    schedule = MedicineSchedule(
        id=1,
        medicine_id=100,
        time="08:30",
        days_of_week="*",
        snooze_minutes=10,
        remind_until_confirmed=True,
    )
    scheduler._schedule_row(schedule, "UTC")
    jobs = scheduler._scheduler.get_jobs()
    assert len(jobs) == 1
    assert jobs[0].id == "schedule:1:daily"


def test_scheduler_creates_weekday_jobs():
    scheduler = ReminderScheduler()
    schedule = MedicineSchedule(
        id=2,
        medicine_id=200,
        time="20:45",
        days_of_week="0,2,4",
        snooze_minutes=10,
        remind_until_confirmed=False,
    )
    scheduler._schedule_row(schedule, "UTC")
    jobs = scheduler._scheduler.get_jobs()
    assert len(jobs) == 3
    assert {job.id for job in jobs} == {
        "schedule:2:day:0",
        "schedule:2:day:2",
        "schedule:2:day:4",
    }


def test_recurring_reload_does_not_remove_snooze_job():
    scheduler = ReminderScheduler()
    scheduler._schedule_snooze_job("evt-1", datetime.now(UTC) + timedelta(minutes=5))
    schedule = MedicineSchedule(id=3, medicine_id=300, time="09:15", days_of_week="*")
    scheduler._schedule_row(schedule, "UTC")

    for job in scheduler._scheduler.get_jobs():
        if job.id.startswith("schedule:"):
            job.remove()

    assert [job.id for job in scheduler._scheduler.get_jobs()] == ["snooze:evt-1"]
