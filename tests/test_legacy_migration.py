from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

import pytest

from app.database.migrations import ensure_sqlite_compatibility


@pytest.mark.asyncio
async def test_legacy_sqlite_tables_receive_fullstack_columns(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'legacy.db'}")
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "CREATE TABLE users (id INTEGER PRIMARY KEY, telegram_id INTEGER, "
                "timezone VARCHAR(64), default_snooze_minutes INTEGER, "
                "remind_until_confirmed BOOLEAN)"
            )
        )
        await connection.execute(
            text(
                "CREATE TABLE medicines (id INTEGER PRIMARY KEY, user_id INTEGER, "
                "name VARCHAR(128), dosage_text VARCHAR(128), is_active BOOLEAN)"
            )
        )
        await connection.execute(
            text(
                "CREATE TABLE medicine_schedules (id INTEGER PRIMARY KEY, "
                "medicine_id INTEGER, time VARCHAR(5), days_of_week VARCHAR(32), "
                "snooze_minutes INTEGER, remind_until_confirmed BOOLEAN)"
            )
        )
        await connection.execute(
            text(
                "CREATE TABLE reminder_dispatch_logs (id INTEGER PRIMARY KEY, "
                "medicine_id INTEGER, schedule_id INTEGER, scheduled_ts INTEGER)"
            )
        )
        await connection.execute(
            text(
                "CREATE TABLE intake_logs (id INTEGER PRIMARY KEY, medicine_id INTEGER, "
                "scheduled_at DATETIME, status VARCHAR(16), responded_at DATETIME)"
            )
        )
        await connection.execute(
            text(
                "INSERT INTO users (id, telegram_id, timezone, default_snooze_minutes, "
                "remind_until_confirmed) VALUES (1, 1001, 'UTC', 25, 1)"
            )
        )
        await connection.execute(
            text(
                "INSERT INTO medicines (id, user_id, name, dosage_text, is_active) "
                "VALUES (1, 1, 'Existing', '1', 1)"
            )
        )
        await connection.execute(
            text(
                "INSERT INTO medicine_schedules (id, medicine_id, time, days_of_week, "
                "snooze_minutes, remind_until_confirmed) VALUES (1, 1, '09:00', '*', 10, 1)"
            )
        )
        await ensure_sqlite_compatibility(connection)

        migrated_snooze_minutes = await connection.scalar(
            text("SELECT snooze_minutes FROM medicine_schedules WHERE id = 1")
        )
        medicine_columns = {
            row[1] for row in (await connection.execute(text("PRAGMA table_info(medicines)"))).all()
        }
        dispatch_columns = {
            row[1]
            for row in (
                await connection.execute(text("PRAGMA table_info(reminder_dispatch_logs)"))
            ).all()
        }

    await engine.dispose()
    assert migrated_snooze_minutes == 25
    assert {"client_medicine_id", "updated_at", "deleted_at"} <= medicine_columns
    assert {"event_id", "status", "chat_id", "message_id", "resolved_at", "snoozed_until"} <= dispatch_columns
