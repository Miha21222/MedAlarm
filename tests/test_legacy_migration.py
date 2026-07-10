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
        await ensure_sqlite_compatibility(connection)

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
    assert {"client_medicine_id", "updated_at", "deleted_at"} <= medicine_columns
    assert {"event_id", "status", "chat_id", "message_id", "resolved_at", "snoozed_until"} <= dispatch_columns
