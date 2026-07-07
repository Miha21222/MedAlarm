from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TelegramAuthRequest(BaseModel):
    init_data: str


class SchedulePayload(BaseModel):
    time: str = Field(pattern=r"^\d{2}:\d{2}$")
    days_of_week: str = "*"
    snooze_minutes: int | None = Field(default=None, ge=1, le=180)
    remind_until_confirmed: bool | None = None


class MedicinePayload(BaseModel):
    client_medicine_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    dosage_text: str = Field(min_length=1, max_length=128)
    comment: str | None = None
    is_active: bool = True
    updated_at: datetime
    deleted_at: datetime | None = None
    schedules: list[SchedulePayload] = []


class MedicineBatchPayload(BaseModel):
    medicines: list[MedicinePayload]


class SettingsPatch(BaseModel):
    language: str | None = Field(default=None, pattern="^(ru|uk|en)$")
    timezone: str | None = None
    default_snooze_minutes: int | None = Field(default=None, ge=1, le=180)
    remind_until_confirmed: bool | None = None


class ReminderActionPayload(BaseModel):
    action: str = Field(pattern="^(taken|skipped)$")
