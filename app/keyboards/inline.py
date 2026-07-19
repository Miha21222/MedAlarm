from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.config import load_settings


def open_mini_app_keyboard(mini_app_url: str | None = None) -> InlineKeyboardMarkup:
    url = load_settings().mini_app_url if mini_app_url is None else mini_app_url
    rows: list[list[InlineKeyboardButton]] = []
    if url.startswith("https://"):
        rows.append([InlineKeyboardButton(text="💊 Открыть MedAlarm", web_app=WebAppInfo(url=url))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reminder_keyboard(
    medicine_id: int,
    schedule_id: int,
    scheduled_ts: int,
    snooze_minutes: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Принял",
                    callback_data=f"rem:taken:{medicine_id}:{schedule_id}:{scheduled_ts}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"⏰ Напомнить через {snooze_minutes} минут",
                    callback_data=f"rem:snooze:{medicine_id}:{schedule_id}:{scheduled_ts}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⏭ Пропустить",
                    callback_data=f"rem:skipped:{medicine_id}:{schedule_id}:{scheduled_ts}",
                )
            ],
        ]
    )
