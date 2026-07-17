from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class TelegramAuthRequest(BaseModel):
    init_data: str


class SchedulePayload(BaseModel):
    time: str = Field(pattern=r"^\d{2}:\d{2}$")
    days_of_week: str = "*"
    snooze_minutes: int | None = Field(default=None, ge=1, le=180)
    remind_until_confirmed: bool | None = None

    @field_validator("time")
    @classmethod
    def validate_time(cls, value: str) -> str:
        hour, minute = (int(part) for part in value.split(":"))
        if hour > 23 or minute > 59:
            raise ValueError("time must be a valid 24-hour time")
        return value

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, value: str) -> str:
        if value == "*":
            return value
        parts = value.split(",")
        if not parts or any(not part.isdigit() or int(part) not in range(7) for part in parts):
            raise ValueError("days_of_week must be '*' or comma-separated values from 0 to 6")
        if len(set(parts)) != len(parts):
            raise ValueError("days_of_week cannot contain duplicates")
        return value


class MedicineCatalogSnapshot(BaseModel):
    source: str = Field(pattern="^moh_state_register$")
    source_id: str = Field(min_length=1, max_length=64)
    trade_name: str = Field(min_length=1, max_length=512)
    inn: str | None = Field(default=None, max_length=512)
    form: str | None = Field(default=None, max_length=10000)
    dispensing_conditions: str | None = Field(default=None, max_length=256)
    active_ingredients: str | None = Field(default=None, max_length=10000)
    pharmacotherapeutic_group: str | None = Field(default=None, max_length=10000)
    atc_codes: str | None = Field(default=None, max_length=128)
    applicant: str | None = Field(default=None, max_length=10000)
    manufacturer: str | None = Field(default=None, max_length=10000)
    registration_number: str | None = Field(default=None, max_length=128)
    valid_from: str | None = Field(default=None, max_length=32)
    valid_until: str | None = Field(default=None, max_length=64)
    early_termination: str | None = Field(default=None, max_length=32)
    instruction_url: str | None = Field(default=None, max_length=2000)


class MedicinePayload(BaseModel):
    client_medicine_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=128)
    dosage_text: str = Field(min_length=1, max_length=128)
    comment: str | None = None
    catalog: MedicineCatalogSnapshot | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime
    deleted_at: datetime | None = None
    schedules: list[SchedulePayload] = []


class MedicineBatchPayload(BaseModel):
    medicines: list[MedicinePayload]


class SettingsPatch(BaseModel):
    language: str | None = Field(default=None, pattern="^(ru|uk|en)$")
    text_size: str | None = Field(default=None, pattern="^(small|regular|large)$")
    timezone: str | None = None
    default_snooze_minutes: int | None = Field(default=None, ge=1, le=180)
    remind_until_confirmed: bool | None = None


class ReminderActionPayload(BaseModel):
    action: str = Field(pattern="^(taken|skipped)$")


class FeedbackCreate(BaseModel):
    kind: str = Field(pattern="^(rating|bug)$")
    rating: int | None = Field(default=None, ge=1, le=5)
    message: str | None = Field(default=None, max_length=5000)
    diagnostic_context: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_kind_fields(self) -> "FeedbackCreate":
        if self.kind == "rating" and self.rating is None:
            raise ValueError("rating is required for rating feedback")
        if self.kind == "bug" and not (self.message and self.message.strip()):
            raise ValueError("message is required for bug reports")
        if self.message is not None:
            self.message = self.message.strip() or None
        return self
