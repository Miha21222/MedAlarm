from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BufferedInputFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.database.models import Feedback, User

logger = logging.getLogger(__name__)

MAX_SCREENSHOT_BYTES = 8 * 1024 * 1024
SCREENSHOT_DIR = Path("data/feedback_screenshots").resolve()
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
TELEGRAM_CAPTION_LIMIT = 1024


def format_feedback_text(feedback: Feedback, user: User) -> str:
    handle = f"@{user.username}" if user.username else user.first_name or "unknown"
    author = f"{handle} (telegram_id={user.telegram_id})"
    if feedback.kind == "rating":
        lines = [f"⭐ New MedAlarm rating: {feedback.rating}/5", f"From: {author}"]
        if feedback.message:
            lines.append(f"Comment: {feedback.message}")
    else:
        lines = ["🐞 New MedAlarm bug report", f"From: {author}", f"Description: {feedback.message}"]
    if feedback.diagnostic_context:
        lines.extend(["", "Technical context:", feedback.diagnostic_context])
    return "\n".join(lines)


async def create_feedback(
    session: AsyncSession,
    user: User,
    *,
    kind: str,
    rating: int | None,
    message: str | None,
    diagnostic_context: str | None,
    image_bytes: bytes | None,
    image_extension: str | None,
) -> Feedback:
    feedback = Feedback(
        user_id=user.id,
        kind=kind,
        rating=rating,
        message=message,
        diagnostic_context=diagnostic_context,
    )
    session.add(feedback)
    await session.flush()
    if image_bytes is not None and image_extension is not None:
        SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        saved_path = SCREENSHOT_DIR / f"{feedback.id}{image_extension}"
        saved_path.write_bytes(image_bytes)
        feedback.screenshot_path = str(saved_path)
        await session.flush()
    return feedback


async def notify_feedback(
    feedback: Feedback,
    user: User,
    settings: Settings,
    *,
    image_bytes: bytes | None = None,
    image_filename: str | None = None,
) -> None:
    """Best-effort relay; the persisted database row remains authoritative."""
    if not settings.bot_token or settings.feedback_chat_id == 0:
        logger.warning("Skip feedback notification id=%s: Telegram relay is not configured", feedback.id)
        return

    topic_id = settings.feedback_topic_id if feedback.kind == "rating" else settings.bug_report_topic_id
    text = format_feedback_text(feedback, user)
    bot = Bot(token=settings.bot_token)
    try:
        if image_bytes is not None:
            await bot.send_photo(
                chat_id=settings.feedback_chat_id,
                message_thread_id=topic_id,
                photo=BufferedInputFile(image_bytes, filename=image_filename or "screenshot.jpg"),
                caption=text[:TELEGRAM_CAPTION_LIMIT],
            )
        else:
            await bot.send_message(
                chat_id=settings.feedback_chat_id,
                message_thread_id=topic_id,
                text=text[:4096],
            )
    except TelegramAPIError as exc:
        logger.warning("Feedback relay failed for id=%s: %s", feedback.id, exc)
    except Exception:
        logger.exception("Unexpected feedback relay failure for id=%s", feedback.id)
    finally:
        await bot.session.close()
