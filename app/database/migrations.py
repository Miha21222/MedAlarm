from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def _columns(connection: AsyncConnection, table: str) -> set[str]:
    rows = await connection.execute(text(f"PRAGMA table_info({table})"))
    return {row[1] for row in rows}


async def _add_columns(
    connection: AsyncConnection,
    table: str,
    definitions: dict[str, str],
) -> None:
    existing = await _columns(connection, table)
    for name, sql_type in definitions.items():
        if name not in existing:
            await connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))


async def ensure_sqlite_compatibility(connection: AsyncConnection) -> None:
    if connection.dialect.name != "sqlite":
        return

    await _add_columns(
        connection,
        "users",
        {
            "language": "VARCHAR(8) DEFAULT 'ru'",
            "text_size": "VARCHAR(16) DEFAULT 'regular'",
        },
    )
    await _add_columns(
        connection,
        "medicines",
        {
            "client_medicine_id": "VARCHAR(64)",
            "updated_at": "DATETIME",
            "deleted_at": "DATETIME",
            "catalog_snapshot": "JSON",
        },
    )
    await _add_columns(
        connection,
        "reminder_dispatch_logs",
        {
            "event_id": "VARCHAR(64)",
            "status": "VARCHAR(16) DEFAULT 'sent'",
            "chat_id": "INTEGER",
            "message_id": "INTEGER",
            "resolved_at": "DATETIME",
            "snoozed_until": "DATETIME",
        },
    )
    await _add_columns(
        connection,
        "intake_logs",
        {"reminder_event_id": "INTEGER"},
    )

    await connection.execute(
        text("UPDATE medicines SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL")
    )
    medicine_rows = await connection.execute(
        text("SELECT id FROM medicines WHERE client_medicine_id IS NULL")
    )
    for (medicine_id,) in medicine_rows:
        await connection.execute(
            text("UPDATE medicines SET client_medicine_id = :value WHERE id = :id"),
            {"value": str(uuid.uuid4()), "id": medicine_id},
        )
    dispatch_rows = await connection.execute(
        text("SELECT id FROM reminder_dispatch_logs WHERE event_id IS NULL")
    )
    for (dispatch_id,) in dispatch_rows:
        await connection.execute(
            text("UPDATE reminder_dispatch_logs SET event_id = :value WHERE id = :id"),
            {"value": str(uuid.uuid4()), "id": dispatch_id},
        )

    await connection.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_medicine_user_client_id "
            "ON medicines(user_id, client_medicine_id)"
        )
    )
    await connection.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_dispatch_event_id "
            "ON reminder_dispatch_logs(event_id)"
        )
    )
    await connection.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_reminder_dispatch_logs_snoozed_until "
            "ON reminder_dispatch_logs(snoozed_until)"
        )
    )
    await connection.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_intake_reminder_event "
            "ON intake_logs(reminder_event_id) WHERE reminder_event_id IS NOT NULL"
        )
    )
