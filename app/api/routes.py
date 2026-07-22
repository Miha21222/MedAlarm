from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.auth import create_access_token, validate_telegram_init_data
from app.api.dependencies import get_current_user, get_session
from app.api.schemas import (
    MedicineBatchPayload,
    MedicinePayload,
    FeedbackCreate,
    ReminderActionPayload,
    ReminderConfigPatch,
    TelegramAuthRequest,
)
from app.config import load_settings
from app.database.models import CatalogMedicine, IntakeLog, Medicine, ReminderDispatchLog, User
from app.services.feedback_service import (
    ALLOWED_IMAGE_TYPES,
    MAX_SCREENSHOT_BYTES,
    create_feedback,
    notify_feedback,
)
from app.services.intake_service import IntakeService
from app.services.medicine_catalog_service import MedicineCatalogService
from app.services.medicine_sync_service import MedicineSyncPayload, MedicineSyncService, ScheduleSyncPayload
from app.services.reminder_action_service import ReminderActionService
from app.services.user_service import UserService
from app.utils.datetime_utils import validate_timezone


router = APIRouter(prefix="/api/v1")


def _serialize_medicine(medicine: Medicine) -> dict[str, object]:
    return {
        "client_medicine_id": medicine.client_medicine_id,
        "name": medicine.name,
        "dosage_text": medicine.dosage_text,
        "comment": medicine.comment,
        "catalog": medicine.catalog_snapshot,
        "is_active": medicine.is_active,
        "created_at": medicine.created_at,
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
        catalog=payload.catalog.model_dump() if payload.catalog else None,
        is_active=payload.is_active,
        created_at=payload.created_at,
        updated_at=payload.updated_at,
        deleted_at=payload.deleted_at,
        schedules=[ScheduleSyncPayload(**slot.model_dump()) for slot in payload.schedules],
    )


def _serialize_catalog_medicine(medicine: CatalogMedicine) -> dict[str, object]:
    return {
        "source": "moh_state_register",
        "source_id": medicine.source_id,
        "trade_name": medicine.trade_name,
        "inn": medicine.inn,
        "form": medicine.form,
        "dispensing_conditions": medicine.dispensing_conditions,
        "active_ingredients": medicine.active_ingredients,
        "pharmacotherapeutic_group": medicine.pharmacotherapeutic_group,
        "atc_codes": medicine.atc_codes,
        "applicant": medicine.applicant,
        "manufacturer": medicine.manufacturer,
        "registration_number": medicine.registration_number,
        "valid_from": medicine.valid_from,
        "valid_until": medicine.valid_until,
        "early_termination": medicine.early_termination,
        "instruction_url": medicine.instruction_url,
    }


@router.get("/catalog/status")
async def catalog_status(session: AsyncSession = Depends(get_session)) -> dict[str, object]:
    return await MedicineCatalogService.status(session)


@router.get("/catalog/medicines")
async def search_catalog(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=20, ge=1, le=30),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    status_payload = await MedicineCatalogService.status(session)
    if not status_payload["ready"]:
        raise HTTPException(
            status_code=503,
            detail="Medicine catalogue is not imported; run python -m app.catalog_update",
        )
    medicines = await MedicineCatalogService.search(session, q, limit)
    return {"items": [_serialize_catalog_medicine(item) for item in medicines], "source": status_payload}


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
    }


def _serialize_reminder_config(user: User) -> dict[str, object]:
    return {
        "language": user.language,
        "timezone": user.timezone,
        "default_snooze_minutes": user.default_snooze_minutes,
        "remind_until_confirmed": user.remind_until_confirmed,
    }


async def _user_medicine_snapshot(session: AsyncSession, user_id: int) -> list[Medicine]:
    result = await session.execute(
        select(Medicine)
        .where(Medicine.user_id == user_id)
        .options(selectinload(Medicine.schedules))
        .order_by(Medicine.updated_at.asc())
    )
    return list(result.scalars())


@router.get("/sync/bootstrap")
async def sync_bootstrap(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    medicines = await _user_medicine_snapshot(session, user.id)
    return {
        "medicines": [_serialize_medicine(item) for item in medicines],
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
    for item in payload.medicines:
        await MedicineSyncService.apply(session, user, _sync_payload(item))

    # Match PocketMind's proven bootstrap contract: a batch push returns the
    # complete account snapshot, not merely the submitted rows. Every device
    # can therefore merge one authoritative response into its local cache.
    medicines = await _user_medicine_snapshot(session, user.id)
    return {
        "medicines": [_serialize_medicine(item) for item in medicines],
        "server_time": datetime.now(UTC),
    }


@router.patch("/reminders/config")
async def patch_reminder_config(
    payload: ReminderConfigPatch,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    # This is a runtime projection, not a server-owned app-settings record.
    # The browser remains authoritative and retries the complete reminder
    # snapshot after reconnecting.
    if payload.timezone is not None:
        if not validate_timezone(payload.timezone):
            raise HTTPException(status_code=422, detail="Invalid IANA timezone")
        updated_user = await UserService.update_timezone(
            session, user.telegram_id, payload.timezone
        )
        if updated_user is not None:
            user = updated_user
    if payload.language is not None:
        user.language = payload.language
    if payload.default_snooze_minutes is not None:
        updated_user = await UserService.update_snooze_minutes(
            session, user.telegram_id, payload.default_snooze_minutes
        )
        if updated_user is not None:
            user = updated_user
    if payload.remind_until_confirmed is not None:
        updated_user = await UserService.update_repeat_mode(
            session, user.telegram_id, payload.remind_until_confirmed
        )
        if updated_user is not None:
            user = updated_user
    return _serialize_reminder_config(user)


@router.get("/dashboard/today")
async def dashboard_today(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    local_date = datetime.now(ZoneInfo(user.timezone)).date()
    doses = await IntakeService.today_doses(session, user.id, local_date, user.timezone)
    return {
        "items": [
            {
                "client_medicine_id": dose.medicine.client_medicine_id,
                "time": dose.schedule.time,
                "days_of_week": dose.schedule.days_of_week,
                "scheduled_at": dose.scheduled_at,
                "status": dose.status,
                "event_id": dose.event_id,
                "actionable": dose.actionable,
            }
            for dose in doses
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
    logs = await IntakeService.history(session, user.id, period=period, timezone_name=user.timezone)
    dispatch_ids = [log.reminder_event_id for log in logs if log.reminder_event_id is not None]
    event_ids: dict[int, str] = {}
    if dispatch_ids:
        dispatches = await session.execute(
            select(ReminderDispatchLog).where(ReminderDispatchLog.id.in_(dispatch_ids))
        )
        event_ids = {dispatch.id: dispatch.event_id for dispatch in dispatches.scalars()}
    return {
        "items": [
            {
                "event_id": event_ids.get(log.reminder_event_id) if log.reminder_event_id is not None else None,
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


@router.post("/feedback")
async def submit_feedback(
    kind: str = Form(...),
    rating: int | None = Form(default=None),
    message: str | None = Form(default=None),
    diagnostic_context: str | None = Form(default=None),
    screenshot: UploadFile | None = File(default=None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    try:
        payload = FeedbackCreate(
            kind=kind,
            rating=rating,
            message=message,
            diagnostic_context=diagnostic_context,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    image_bytes: bytes | None = None
    image_extension: str | None = None
    if screenshot is not None:
        image_extension = ALLOWED_IMAGE_TYPES.get(screenshot.content_type or "")
        if image_extension is None:
            raise HTTPException(status_code=400, detail="Screenshot must be JPEG, PNG, or WebP")
        image_bytes = await screenshot.read(MAX_SCREENSHOT_BYTES + 1)
        if not image_bytes:
            raise HTTPException(status_code=400, detail="Screenshot is empty")
        if len(image_bytes) > MAX_SCREENSHOT_BYTES:
            raise HTTPException(status_code=413, detail="Screenshot is larger than 8 MB")

    feedback = await create_feedback(
        session,
        user,
        kind=payload.kind,
        rating=payload.rating,
        message=payload.message,
        diagnostic_context=payload.diagnostic_context,
        image_bytes=image_bytes,
        image_extension=image_extension,
    )
    await notify_feedback(
        feedback,
        user,
        load_settings(),
        image_bytes=image_bytes,
        image_filename=f"screenshot{image_extension}" if image_extension else None,
    )
    return {"id": feedback.id}
