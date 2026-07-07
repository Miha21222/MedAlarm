from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import create_access_token, validate_telegram_init_data
from app.api.dependencies import get_current_user, get_session
from app.api.schemas import (
    MedicineBatchPayload,
    MedicinePayload,
    ReminderActionPayload,
    SettingsPatch,
    TelegramAuthRequest,
)
from app.config import load_settings
from app.database.models import IntakeLog, Medicine, ReminderDispatchLog, User
from app.services.intake_service import IntakeService
from app.services.medicine_sync_service import MedicineSyncPayload, MedicineSyncService, ScheduleSyncPayload
from app.services.reminder_action_service import ReminderActionService
from app.services.schedule_service import ScheduleService
from app.services.user_service import UserService
from app.utils.datetime_utils import validate_timezone


router = APIRouter(prefix="/api/v1")


def _serialize_medicine(medicine: Medicine) -> dict[str, object]:
    return {
        "client_medicine_id": medicine.client_medicine_id,
        "name": medicine.name,
        "dosage_text": medicine.dosage_text,
        "comment": medicine.comment,
        "is_active": medicine.is_active,
        "updated_at": medicine.updated_at,
        "deleted_at": medicine.deleted_at,
        "schedules": [
            {
                "time": slot.time,
                "days_of_week": slot.days_of_week,
                "snooze_minutes": slot.snooze_minutes,
                "remind_until_confirmed": slot.remind_until_confirmed,
            }
            for slot in medicine.schedules
        ],
    }


def _sync_payload(payload: MedicinePayload) -> MedicineSyncPayload:
    return MedicineSyncPayload(
        client_medicine_id=payload.client_medicine_id,
        name=payload.name,
        dosage_text=payload.dosage_text,
        comment=payload.comment,
        is_active=payload.is_active,
        updated_at=payload.updated_at,
        deleted_at=payload.deleted_at,
        schedules=[ScheduleSyncPayload(**slot.model_dump()) for slot in payload.schedules],
    )


@router.post("/auth/telegram")
async def telegram_auth(
    payload: TelegramAuthRequest,
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    settings = load_settings()
    try:
        identity = validate_telegram_init_data(payload.init_data, settings.bot_token)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    user = await UserService.register_or_update_user(
        session,
        telegram_id=int(identity["id"]),
        username=identity.get("username"),
        first_name=identity.get("first_name"),
        last_name=identity.get("last_name"),
        default_timezone=settings.default_timezone,
    )
    token = create_access_token(
        user.telegram_id,
        settings.jwt_secret,
        settings.jwt_expire_minutes * 60,
    )
    return {"access_token": token, "token_type": "bearer", "user": _serialize_user(user)}


def _serialize_user(user: User) -> dict[str, object]:
    return {
        "telegram_id": user.telegram_id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "language": user.language,
        "timezone": user.timezone,
        "default_snooze_minutes": user.default_snooze_minutes,
        "remind_until_confirmed": user.remind_until_confirmed,
    }


@router.get("/sync/bootstrap")
async def sync_bootstrap(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    result = await session.execute(
        select(Medicine)
        .where(Medicine.user_id == user.id)
        .options(selectinload(Medicine.schedules))
        .order_by(Medicine.updated_at.asc())
    )
    return {
        "medicines": [_serialize_medicine(item) for item in result.scalars()],
        "server_time": datetime.now(UTC),
    }


@router.put("/sync/medicines/{client_medicine_id}")
async def sync_medicine(
    client_medicine_id: str,
    payload: MedicinePayload,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    if payload.client_medicine_id != client_medicine_id:
        raise HTTPException(status_code=400, detail="Medicine ID mismatch")
    applied, medicine = await MedicineSyncService.apply(session, user, _sync_payload(payload))
    return {"applied": applied, "medicine": _serialize_medicine(medicine)}


@router.post("/sync/batch")
async def sync_batch(
    payload: MedicineBatchPayload,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    items = []
    for item in payload.medicines:
        applied, medicine = await MedicineSyncService.apply(session, user, _sync_payload(item))
        items.append({"applied": applied, "medicine": _serialize_medicine(medicine)})
    return {"items": items, "server_time": datetime.now(UTC)}


@router.get("/settings/me")
async def get_settings(user: User = Depends(get_current_user)) -> dict[str, object]:
    return _serialize_user(user)


@router.patch("/settings/me")
async def patch_settings(
    payload: SettingsPatch,
    user: User = Depends(get_current_user),
) -> dict[str, object]:
    if payload.timezone is not None:
        if not validate_timezone(payload.timezone):
            raise HTTPException(status_code=422, detail="Invalid IANA timezone")
        user.timezone = payload.timezone
    if payload.language is not None:
        user.language = payload.language
    if payload.default_snooze_minutes is not None:
        user.default_snooze_minutes = payload.default_snooze_minutes
    if payload.remind_until_confirmed is not None:
        user.remind_until_confirmed = payload.remind_until_confirmed
    return _serialize_user(user)


@router.get("/dashboard/today")
async def dashboard_today(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    local_date = datetime.now(ZoneInfo(user.timezone)).date()
    medicines = await ScheduleService.get_user_today_medicines(session, user.id, local_date)
    statuses = await IntakeService.today_status_by_medicine(session, user.id, local_date, user.timezone)
    return {
        "items": [
            {
                **_serialize_medicine(medicine),
                "status": statuses.get(medicine.id, "pending"),
            }
            for medicine in medicines
        ]
    }


@router.get("/dashboard/adherence")
async def adherence(
    period: str = Query(default="7d", pattern="^(7d|30d)$"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    days = 7 if period == "7d" else 30
    since = datetime.now(UTC) - timedelta(days=days)
    result = await session.execute(
        select(IntakeLog.status, func.count(IntakeLog.id))
        .join(Medicine, Medicine.id == IntakeLog.medicine_id)
        .where(Medicine.user_id == user.id, IntakeLog.scheduled_at >= since)
        .group_by(IntakeLog.status)
    )
    counts = {status: count for status, count in result}
    resolved = counts.get("taken", 0) + counts.get("skipped", 0) + counts.get("missed", 0)
    return {
        "period": period,
        "counts": counts,
        "adherence_percent": round((counts.get("taken", 0) / resolved) * 100) if resolved else 0,
    }


@router.get("/history")
async def history(
    period: str = Query(default="week", pattern="^(today|week|month)$"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    logs = await IntakeService.history(session, user.id, period=period)
    return {
        "items": [
            {
                "event_id": log.reminder_event_id,
                "medicine": log.medicine.name,
                "scheduled_at": log.scheduled_at,
                "responded_at": log.responded_at,
                "status": log.status,
            }
            for log in logs
        ]
    }


@router.post("/reminder-events/{event_id}/actions")
async def reminder_action(
    event_id: str,
    payload: ReminderActionPayload,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    try:
        result = await ReminderActionService.resolve(session, user.id, event_id, payload.action)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "event_id": result.event_id,
        "status": result.status,
        "intake_id": result.intake_id,
    }
