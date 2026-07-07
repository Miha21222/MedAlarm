from __future__ import annotations

import asyncio
import logging

from app.bot import create_bot_and_dispatcher, setup_bot_commands
from app.config import load_settings
from app.database.session import init_db


async def run() -> None:
    settings = load_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is empty")
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
    await init_db()
    bot, dispatcher = create_bot_and_dispatcher(settings)
    await setup_bot_commands(bot)
    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run())
