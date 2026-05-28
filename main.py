from __future__ import annotations

import asyncio
import logging

from app.bot import create_bot_and_dispatcher, setup_bot_commands
from app.config import load_settings
from app.database.session import init_db
from app.scheduler.jobs import ReminderScheduler
from app.scheduler.setup import set_scheduler


async def run() -> None:
    settings = load_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is empty. Set it in .env")

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    await init_db()
    bot, dp = create_bot_and_dispatcher(settings)
    await setup_bot_commands(bot)

    reminder_scheduler = ReminderScheduler()
    set_scheduler(reminder_scheduler)
    await reminder_scheduler.start(bot)

    try:
        await dp.start_polling(bot)
    finally:
        await reminder_scheduler.stop()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run())
