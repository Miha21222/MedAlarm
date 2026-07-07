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
    jwt_secret: str
    jwt_expire_minutes: int
    mini_app_url: str
    cors_allowed_origins: tuple[str, ...]


def build_database_url(raw_path: str) -> str:
    db_path = Path(raw_path).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


DEFAULT_JWT_SECRET = "change-me-in-production"


def load_settings() -> Settings:
    db_path = os.getenv("DB_PATH", "./data/medalarm.db")
    app_env = os.getenv("APP_ENV", "dev")
    jwt_secret = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    if app_env != "dev" and (not jwt_secret or jwt_secret == DEFAULT_JWT_SECRET):
        raise RuntimeError(
            "JWT_SECRET must be set to a real secret when APP_ENV is not 'dev'. "
            "Refusing to start with the insecure default."
        )
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        database_url=os.getenv("DATABASE_URL", build_database_url(db_path)),
        default_timezone=os.getenv("DEFAULT_TIMEZONE", "UTC"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        app_env=app_env,
        jwt_secret=jwt_secret,
        jwt_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "1440")),
        mini_app_url=os.getenv("MINI_APP_URL", "http://localhost:5173"),
        cors_allowed_origins=tuple(
            item.strip()
            for item in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
            if item.strip()
        ),
    )
