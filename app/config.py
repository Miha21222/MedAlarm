from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class Settings:
    bot_token: str
    database_url: str
    default_timezone: str
    log_level: str
    app_env: str


def build_database_url(raw_path: str) -> str:
    db_path = Path(raw_path).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


def load_settings() -> Settings:
    db_path = os.getenv("DB_PATH", "./data/medalarm.db")
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        database_url=os.getenv("DATABASE_URL", build_database_url(db_path)),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "UTC"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        app_env=os.getenv("APP_ENV", "dev"),
    )

