from __future__ import annotations

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    medicines: Mapped[list["Medicine"]] = relationship(back_populates="user")


class Medicine(Base):
    __tablename__ = "medicines"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    dosage_text: Mapped[str] = mapped_column(String(128))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"), index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(16))
    responded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    medicine: Mapped[Medicine] = relationship(back_populates="intake_logs")


class ReminderDispatchLog(Base):
    __tablename__ = "reminder_dispatch_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.id"), index=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("medicine_schedules.id"), index=True)
    scheduled_ts: Mapped[int] = mapped_column(Integer, index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    medicine: Mapped[Medicine] = relationship(back_populates="reminder_dispatch_logs")
    schedule: Mapped[MedicineSchedule] = relationship(back_populates="reminder_dispatch_logs")
