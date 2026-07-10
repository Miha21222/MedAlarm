from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    default_snooze_minutes: Mapped[int] = mapped_column(Integer, default=10)
    remind_until_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String(8), default="ru")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    medicines: Mapped[list["Medicine"]] = relationship(back_populates="user")
    feedback_items: Mapped[list["Feedback"]] = relationship(back_populates="user")


class Medicine(Base):
    __tablename__ = "medicines"
    __table_args__ = (UniqueConstraint("user_id", "client_medicine_id", name="uq_medicine_user_client_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    client_medicine_id: Mapped[str] = mapped_column(
        String(64), default=lambda: str(uuid.uuid4()), index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    dosage_text: Mapped[str] = mapped_column(String(128))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="medicines")
    schedules: Mapped[list["MedicineSchedule"]] = relationship(
        back_populates="medicine", cascade="all, delete-orphan"
    )
    intake_logs: Mapped[list["IntakeLog"]] = relationship(back_populates="medicine", cascade="all, delete-orphan")
    reminder_dispatch_logs: Mapped[list["ReminderDispatchLog"]] = relationship(
        back_populates="medicine", cascade="all, delete-orphan"
    )


class MedicineSchedule(Base):
    __tablename__ = "medicine_schedules"
    __table_args__ = (UniqueConstraint("medicine_id", "time", "days_of_week", name="uq_schedule_slot"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"), index=True)
    time: Mapped[str] = mapped_column(String(5))
    days_of_week: Mapped[str] = mapped_column(String(32), default="*")
    snooze_minutes: Mapped[int] = mapped_column(Integer, default=10)
    remind_until_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)

    medicine: Mapped[Medicine] = relationship(back_populates="schedules")
    reminder_dispatch_logs: Mapped[list["ReminderDispatchLog"]] = relationship(
        back_populates="schedule", cascade="all, delete-orphan"
    )


class IntakeLog(Base):
    __tablename__ = "intake_logs"
    __table_args__ = (UniqueConstraint("reminder_event_id", name="uq_intake_reminder_event"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"), index=True)
    reminder_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("reminder_dispatch_logs.id"), nullable=True, index=True
    )
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    responded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    medicine: Mapped[Medicine] = relationship(back_populates="intake_logs")


class ReminderDispatchLog(Base):
    __tablename__ = "reminder_dispatch_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(
        String(64), unique=True, default=lambda: str(uuid.uuid4()), index=True
    )
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"), index=True)
    schedule_id: Mapped[int | None] = mapped_column(
        ForeignKey("medicine_schedules.id"), nullable=True, index=True
    )
    scheduled_ts: Mapped[int] = mapped_column(Integer, index=True)
    status: Mapped[str] = mapped_column(String(16), default="sent")
    chat_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    medicine: Mapped[Medicine] = relationship(back_populates="reminder_dispatch_logs")
    schedule: Mapped[MedicineSchedule] = relationship(back_populates="reminder_dispatch_logs")


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnostic_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    user: Mapped[User] = relationship(back_populates="feedback_items")
