from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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
    feedback_chat_id: int
    feedback_topic_id: int
    bug_report_topic_id: int
    catalog_auto_update: bool = False


def build_database_url(raw_path: str) -> str:
    db_path = Path(raw_path).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path.as_posix()}"


DEFAULT_JWT_SECRET = "change-me-in-production"


def load_settings() -> Settings:
    db_path = os.getenv("DB_PATH", "./data/medalarm.db")
    app_env = os.getenv("APP_ENV", "dev")
    jwt_secret = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    bot_token = os.getenv("BOT_TOKEN", "")
    mini_app_url = os.getenv("MINI_APP_URL", "http://localhost:5173")
    jwt_expire_minutes = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))
    default_timezone = os.getenv("DEFAULT_TIMEZONE", "UTC")
    cors_allowed_origins = tuple(
        item.strip()
        for item in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if item.strip()
    )
    try:
        ZoneInfo(default_timezone)
    except ZoneInfoNotFoundError as exc:
        raise RuntimeError("DEFAULT_TIMEZONE must be a valid IANA timezone") from exc
    if jwt_expire_minutes <= 0:
        raise RuntimeError("JWT_EXPIRE_MINUTES must be positive")
    if app_env != "dev":
        if not bot_token:
            raise RuntimeError("BOT_TOKEN must be set in production")
        if jwt_secret == DEFAULT_JWT_SECRET or len(jwt_secret.encode()) < 32:
            raise RuntimeError("JWT_SECRET must contain at least 32 bytes in production")
        if urlparse(mini_app_url).scheme != "https":
            raise RuntimeError("MINI_APP_URL must use HTTPS in production")
        if not cors_allowed_origins:
            raise RuntimeError("CORS_ALLOWED_ORIGINS must not be empty in production")
        for origin in cors_allowed_origins:
            parsed = urlparse(origin)
            if parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"}:
                raise RuntimeError("Production CORS origins must be HTTPS origins without paths")
            if parsed.hostname in {"localhost", "127.0.0.1"} or "*" in origin:
                raise RuntimeError("Production CORS origins cannot use localhost or wildcards")
    return Settings(
        bot_token=bot_token,
        database_url=os.getenv("DATABASE_URL", build_database_url(db_path)),
        default_timezone=default_timezone,
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        app_env=app_env,
        jwt_secret=jwt_secret,
        jwt_expire_minutes=jwt_expire_minutes,
        mini_app_url=mini_app_url,
        cors_allowed_origins=cors_allowed_origins,
        feedback_chat_id=int(os.getenv("FEEDBACK_CHAT_ID", "-1004421534137")),
        feedback_topic_id=int(os.getenv("FEEDBACK_TOPIC_ID", "3")),
        bug_report_topic_id=int(os.getenv("BUG_REPORT_TOPIC_ID", "5")),
        catalog_auto_update=os.getenv("CATALOG_AUTO_UPDATE", "false").lower() in {"1", "true", "yes"},
    )
