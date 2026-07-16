from __future__ import annotations

import argparse
import asyncio

from app.database.session import init_db, session_scope
from app.services.medicine_catalog_service import MedicineCatalogService


async def update_catalog(force: bool = False) -> int:
    await init_db()
    async with session_scope() as session:
        return await MedicineCatalogService.refresh(session, force=force)


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the MOH State Register medicine catalogue")
    parser.add_argument("--force", action="store_true", help="download even when the source is unchanged")
    args = parser.parse_args()
    count = asyncio.run(update_catalog(force=args.force))
    print(f"MOH catalogue ready: {count} records")


if __name__ == "__main__":
    main()
