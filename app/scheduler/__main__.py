from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from app.config import load_settings
from app.database.session import init_db
from app.scheduler.jobs import ReminderScheduler


async def run() -> None:
    settings = load_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is empty")
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    await init_db()
    bot = Bot(settings.bot_token)
    scheduler = ReminderScheduler()
    await scheduler.start(bot)
    try:
        while True:
            await asyncio.sleep(30)
            await scheduler.reload_jobs()
    finally:
        await scheduler.stop()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run())
