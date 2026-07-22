from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict
from datetime import datetime
from typing import Any

from app.database.session import init_db, session_scope
from app.services.dispatch_recovery_service import DispatchRecoveryService


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Cannot serialize {type(value).__name__}")


async def run_command(args: argparse.Namespace) -> dict[str, object]:
    await init_db()
    if args.command == "list":
        async with session_scope() as session:
            rows = await DispatchRecoveryService.list_uncertain(session, limit=args.limit)
        return {"count": len(rows), "dispatches": [asdict(row) for row in rows]}

    action = "confirmed_sent" if args.command == "mark-sent" else "confirmed_failed"
    async with session_scope() as session:
        dispatch = await DispatchRecoveryService.resolve(
            session,
            event_id=args.event_id,
            action=action,
            note=args.note,
            message_id=getattr(args, "message_id", None),
        )
    return {
        "event_id": dispatch.event_id,
        "status": dispatch.status,
        "message_id": dispatch.message_id,
        "recovery_action": dispatch.recovery_action,
        "recovered_at": dispatch.recovered_at,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect and explicitly resolve uncertain reminder deliveries"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="list uncertain dispatches")
    list_parser.add_argument("--limit", type=int, default=100)

    sent_parser = subparsers.add_parser(
        "mark-sent", help="record a delivery that was verified in Telegram"
    )
    sent_parser.add_argument("event_id")
    sent_parser.add_argument("--message-id", type=int, required=True)
    sent_parser.add_argument("--note", required=True)
    sent_parser.add_argument("--yes", action="store_true", help="confirm the state change")

    failed_parser = subparsers.add_parser(
        "mark-failed", help="record that Telegram did not receive the reminder"
    )
    failed_parser.add_argument("event_id")
    failed_parser.add_argument("--note", required=True)
    failed_parser.add_argument("--yes", action="store_true", help="confirm the state change")
    return parser


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    if args.command != "list" and not args.yes:
        parser.error("state-changing commands require --yes")
    try:
        result = asyncio.run(run_command(args))
    except (LookupError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
