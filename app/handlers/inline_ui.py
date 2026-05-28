from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app.config import load_settings
from app.database.session import session_scope
from app.keyboards.inline import (
    history_filter_keyboard,
    history_medicine_filter_keyboard,
    main_menu_keyboard,
    medicine_edit_fields_keyboard,
    medicine_list_keyboard,
    medicine_manage_keyboard,
    medicine_wizard_keyboard,
    one_level_back_keyboard,
    open_menu_keyboard,
    settings_keyboard,
)
from app.scheduler.setup import get_scheduler
from app.services.intake_service import IntakeService
from app.services.medicine_service import MedicineCreatePayload, MedicineService
from app.services.schedule_service import ScheduleService
from app.services.user_service import UserService
from app.utils.datetime_utils import (
    format_days,
    format_times,
    now_in_timezone,
    parse_days_input,
    parse_times_input,
    validate_timezone,
)

router = Router()

SCREEN_MENU = "menu"
SCREEN_MED_LIST = "med_list"
SCREEN_MED_VIEW = "med_view"
SCREEN_MED_EDIT = "med_edit"
SCREEN_MED_ADD = "med_add"
SCREEN_TODAY = "today"
SCREEN_HISTORY = "history"
SCREEN_HISTORY_FILTER = "history_filter"
SCREEN_SETTINGS = "settings"

AWAIT_NONE = ""
AWAIT_ADD_NAME = "add_name"
AWAIT_ADD_DOSAGE = "add_dosage"
AWAIT_ADD_TIMES = "add_times"
AWAIT_ADD_DAYS = "add_days"
AWAIT_ADD_COMMENT = "add_comment"
AWAIT_EDIT_NAME = "edit_name"
AWAIT_EDIT_DOSAGE = "edit_dosage"
AWAIT_EDIT_TIMES = "edit_times"
AWAIT_EDIT_DAYS = "edit_days"
AWAIT_EDIT_COMMENT = "edit_comment"
AWAIT_SET_TZ = "set_tz"
AWAIT_SET_SNOOZE = "set_snooze"


@dataclass(slots=True)
class ScreenRender:
    text: str
    keyboard: InlineKeyboardMarkup


async def _register_user(source: Message | CallbackQuery) -> None:
    user = source.from_user
    if user is None:
        return
    settings = load_settings()
    async with session_scope() as session:
        await UserService.register_or_update_user(
            session=session,
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            default_timezone=settings.default_timezone,
        )


async def _state_get(state: FSMContext, key: str, default: Any = None) -> Any:
    data = await state.get_data()
    return data.get(key, default)


async def _set_screen(state: FSMContext, screen: str, payload: dict[str, Any] | None = None) -> None:
    await state.update_data(current_screen=screen, screen_payload=payload or {})


async def _delete_message_safe(message: Message) -> None:
    try:
        await message.delete()
    except Exception:
        pass


def _is_message_not_modified_error(exc: TelegramBadRequest) -> bool:
    return "message is not modified" in str(exc).lower()


async def _show_panel(
    *,
    state: FSMContext,
    chat_id: int,
    bot,
    text: str,
    keyboard: InlineKeyboardMarkup,
    preferred_message: Message | None = None,
) -> None:
    panel_id = await _state_get(state, "panel_message_id")
    if preferred_message is not None and (panel_id is None or panel_id == preferred_message.message_id):
        try:
            await preferred_message.edit_text(text=text, reply_markup=keyboard)
            await state.update_data(panel_message_id=preferred_message.message_id)
            return
        except TelegramBadRequest as exc:
            if _is_message_not_modified_error(exc):
                return
            pass
    if panel_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=panel_id,
                text=text,
                reply_markup=keyboard,
            )
            return
        except TelegramBadRequest as exc:
            if _is_message_not_modified_error(exc):
                return
            pass
    sent = await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)
    await state.update_data(panel_message_id=sent.message_id)


def _wizard_order(draft: dict[str, Any]) -> list[str]:
    base = ["name", "dosage", "times", "frequency", "comment", "confirm"]
    if draft.get("frequency_mode") == "weekly":
        return ["name", "dosage", "times", "frequency", "days", "comment", "confirm"]
    return base


def _wizard_can_next(step: str, draft: dict[str, Any]) -> bool:
    if step == "name":
        return bool(draft.get("name"))
    if step == "dosage":
        return bool(draft.get("dosage_text"))
    if step == "times":
        return bool(draft.get("times"))
    if step == "frequency":
        return draft.get("frequency_mode") in {"daily", "weekly"}
    if step == "days":
        return bool(draft.get("days_of_week")) and draft.get("days_of_week") != "*"
    if step == "comment":
        return True
    return False


def _wizard_can_save(draft: dict[str, Any]) -> bool:
    required = {"name", "dosage_text", "times", "days_of_week"}
    return required.issubset(set(draft.keys()))


def _wizard_prev_step(step: str, draft: dict[str, Any]) -> str:
    order = _wizard_order(draft)
    idx = order.index(step)
    if idx == 0:
        return step
    return order[idx - 1]


def _wizard_next_step(step: str, draft: dict[str, Any]) -> str:
    order = _wizard_order(draft)
    idx = order.index(step)
    if idx >= len(order) - 1:
        return step
    return order[idx + 1]


def _build_display_number_map(medicines: list[Any]) -> dict[int, int]:
    return {medicine.id: index for index, medicine in enumerate(medicines, start=1)}


def _step_prompt(step: str) -> str:
    prompts = {
        "name": "✍️ Отправьте сообщением название лекарства. Пример: Аденурик.",
        "dosage": "✍️ Отправьте сообщением дозировку. Пример: 1 таблетка.",
        "times": "✍️ Отправьте сообщением время приёма. Пример: 09:00, 21:00.",
        "frequency": "👇 Нажмите кнопку ниже: каждый день или конкретные дни.",
        "days": "✍️ Отправьте сообщением дни недели. Пример: 1,3,5 или пн,ср,пт.",
        "comment": "✍️ Отправьте сообщением комментарий или '-' если не нужен.",
        "confirm": "✅ Проверьте данные и нажмите «Сохранить».",
    }
    return prompts[step]


def _step_to_awaiting(step: str) -> str:
    mapping = {
        "name": AWAIT_ADD_NAME,
        "dosage": AWAIT_ADD_DOSAGE,
        "times": AWAIT_ADD_TIMES,
        "days": AWAIT_ADD_DAYS,
        "comment": AWAIT_ADD_COMMENT,
    }
    return mapping.get(step, AWAIT_NONE)


async def _render_menu() -> ScreenRender:
    return ScreenRender("📋 Главное меню\n\nВыберите раздел.", main_menu_keyboard())


async def _render_medicines_list(telegram_id: int) -> ScreenRender:
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, telegram_id)
        if user is None:
            return ScreenRender("Сначала выполните /start.", main_menu_keyboard())
        medicines = await MedicineService.list_all_user_medicines(session, user.id)
    if not medicines:
        text = "💊 Лекарств пока нет. Нажмите «Добавить лекарство»."
    else:
        display_numbers = _build_display_number_map(medicines)
        lines = ["💊 Ваши лекарства:"]
        for medicine in medicines:
            status = "активно" if medicine.is_active else "неактивно"
            lines.append(f"• №{display_numbers[medicine.id]}. {medicine.name} ({status})")
        text = "\n".join(lines)
    return ScreenRender(text, medicine_list_keyboard(medicines, _build_display_number_map(medicines)))


async def _render_medicine_view(telegram_id: int, medicine_id: int) -> ScreenRender:
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, telegram_id)
        if user is None:
            return ScreenRender("Сначала выполните /start.", main_menu_keyboard())
        medicines = await MedicineService.list_all_user_medicines(session, user.id)
    display_numbers = _build_display_number_map(medicines)
    medicine = next((item for item in medicines if item.id == medicine_id), None)
    if medicine is None:
        return ScreenRender("Лекарство не найдено.", one_level_back_keyboard())
    display_number = display_numbers[medicine.id]
    times = sorted(schedule.time for schedule in medicine.schedules)
    schedule_line = "расписание не задано"
    repeats = "выключены"
    if medicine.schedules:
        schedule_line = f"{format_times(times)}, {format_days(medicine.schedules[0].days_of_week)}"
        repeats = "включены" if medicine.schedules[0].remind_until_confirmed else "выключены"
    status = "активно" if medicine.is_active else "неактивно"
    text = (
        f"Лекарство №{display_number} | {medicine.name}\n"
        f"Дозировка: {medicine.dosage_text}\n"
        f"Расписание: {schedule_line}\n"
        f"Повторы: {repeats}\n"
        f"Статус: {status}\n"
        f"Комментарий: {medicine.comment or '-'}"
    )
    return ScreenRender(text, medicine_manage_keyboard(medicine.id, medicine.is_active))


async def _render_medicine_edit(telegram_id: int, medicine_id: int) -> ScreenRender:
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, telegram_id)
        if user is None:
            return ScreenRender("Сначала выполните /start.", main_menu_keyboard())
        medicines = await MedicineService.list_all_user_medicines(session, user.id)
    display_numbers = _build_display_number_map(medicines)
    medicine = next((item for item in medicines if item.id == medicine_id), None)
    if medicine is None:
        return ScreenRender("Лекарство не найдено.", one_level_back_keyboard())
    return ScreenRender(
        f"Редактирование лекарства №{display_numbers[medicine.id]} ({medicine.name})\nВыберите поле:",
        medicine_edit_fields_keyboard(medicine.id),
    )


async def _render_today(telegram_id: int) -> ScreenRender:
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, telegram_id)
        if user is None:
            return ScreenRender("Сначала выполните /start.", main_menu_keyboard())
        local_date = now_in_timezone(user.timezone).date()
        medicines = await ScheduleService.get_user_today_medicines(session, user.id, local_date)
        status_map = await IntakeService.today_status_by_medicine(
            session=session,
            user_id=user.id,
            local_date=local_date,
            timezone_name=user.timezone,
        )
    if not medicines:
        text = "📅 На сегодня активных приёмов нет."
    else:
        lines = ["📅 Сегодня нужно принять:"]
        for medicine in medicines:
            times = sorted(schedule.time for schedule in medicine.schedules)
            status = status_map.get(medicine.id)
            mark = "✅" if status == "taken" else "❌" if status == "skipped" else "⏳"
            lines.append(f"• {medicine.name} ({medicine.dosage_text}) в {format_times(times)} {mark}")
        text = "\n".join(lines)
    return ScreenRender(text, one_level_back_keyboard())


async def _render_history(telegram_id: int, state: FSMContext) -> ScreenRender:
    period = await _state_get(state, "history_period", "week")
    medicine_id = await _state_get(state, "history_medicine_id")
    page = int(await _state_get(state, "history_page", 0))
    limit = 10
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, telegram_id)
        if user is None:
            return ScreenRender("Сначала выполните /start.", main_menu_keyboard())
        records = await IntakeService.history(
            session=session,
            user_id=user.id,
            period=period,
            medicine_id=medicine_id,
            limit=200,
        )
        medicines = await MedicineService.list_all_user_medicines(session, user.id)
    total_pages = max(1, (len(records) + limit - 1) // limit)
    page = max(0, min(page, total_pages - 1))
    await state.update_data(history_page=page)
    records_part = records[page * limit : page * limit + limit]
    lines = [f"📜 История ({period}):"]
    if not records_part:
        lines.append("Записей нет.")
    else:
        for row in records_part:
            lines.append(
                f"• {row.scheduled_at.strftime('%Y-%m-%d %H:%M')} | {row.medicine.name} | {IntakeService.status_to_emoji(row.status)}"
            )
    return ScreenRender(
        "\n".join(lines),
        history_filter_keyboard(
            period=period,
            page=page,
            total_pages=total_pages,
            has_medicine_filter=bool(medicines),
        ),
    )


async def _render_history_filter(telegram_id: int, state: FSMContext) -> ScreenRender:
    page = int(await _state_get(state, "history_med_page", 0))
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, telegram_id)
        if user is None:
            return ScreenRender("Сначала выполните /start.", main_menu_keyboard())
        medicines = await MedicineService.list_all_user_medicines(session, user.id)
    return ScreenRender("🔎 Выберите лекарство для фильтра:", history_medicine_filter_keyboard(medicines, page=page))


async def _render_settings(telegram_id: int) -> ScreenRender:
    async with session_scope() as session:
        user = await UserService.get_by_telegram_id(session, telegram_id)
        if user is None:
            return ScreenRender("Сначала выполните /start.", main_menu_keyboard())
    text = (
        "⚙️ Настройки:\n"
        f"TZ: {user.timezone}\n"
        f"Snooze: {user.default_snooze_minutes} мин\n"
        f"Повторы: {'on' if user.remind_until_confirmed else 'off'}\n\n"
        "Для TZ и Snooze нажмите кнопку и отправьте новое значение."
    )
    return ScreenRender(text, settings_keyboard())


async def _render_medicine_add(state: FSMContext) -> ScreenRender:
    draft = await _state_get(state, "add_draft", {})
    step = await _state_get(state, "add_step", "name")
    order = _wizard_order(draft)
    index = order.index(step) + 1
    total = len(order)
    awaiting = _step_to_awaiting(step)
    await state.update_data(awaiting_input=awaiting)

    lines = [
        f"🆕 Добавление лекарства (шаг {index}/{total})",
        f"Название: {draft.get('name', '—')}",
        f"Дозировка: {draft.get('dosage_text', '—')}",
        f"Время: {format_times(draft['times']) if draft.get('times') else '—'}",
        f"Режим: {'каждый день' if draft.get('frequency_mode') == 'daily' else 'конкретные дни' if draft.get('frequency_mode') == 'weekly' else '—'}",
        f"Дни: {format_days(draft['days_of_week']) if draft.get('days_of_week') else '—'}",
        f"Комментарий: {draft.get('comment') or '—'}",
        "",
        _step_prompt(step),
    ]
    if awaiting:
        lines.extend(
            [
                "",
                "ℹ️ Сообщение будет обработано и удалено автоматически.",
            ]
        )
    return ScreenRender(
        "\n".join(lines),
        medicine_wizard_keyboard(
            can_prev=step != order[0],
            can_next=_wizard_can_next(step, draft),
            can_save=step == "confirm" and _wizard_can_save(draft),
            show_frequency=step == "frequency",
        ),
    )


async def _render_current(telegram_id: int, state: FSMContext) -> ScreenRender:
    screen = await _state_get(state, "current_screen", SCREEN_MENU)
    payload = await _state_get(state, "screen_payload", {})
    if screen == SCREEN_MED_LIST:
        return await _render_medicines_list(telegram_id)
    if screen == SCREEN_MED_VIEW:
        return await _render_medicine_view(telegram_id, int(payload.get("medicine_id", 0)))
    if screen == SCREEN_MED_EDIT:
        return await _render_medicine_edit(telegram_id, int(payload.get("medicine_id", 0)))
    if screen == SCREEN_MED_ADD:
        return await _render_medicine_add(state)
    if screen == SCREEN_TODAY:
        return await _render_today(telegram_id)
    if screen == SCREEN_HISTORY:
        return await _render_history(telegram_id, state)
    if screen == SCREEN_HISTORY_FILTER:
        return await _render_history_filter(telegram_id, state)
    if screen == SCREEN_SETTINGS:
        return await _render_settings(telegram_id)
    return await _render_menu()


async def _refresh(state: FSMContext, message: Message, telegram_id: int) -> None:
    render = await _render_current(telegram_id, state)
    await _show_panel(
        state=state,
        chat_id=message.chat.id,
        bot=message.bot,
        text=render.text,
        keyboard=render.keyboard,
        preferred_message=message,
    )


async def _refresh_without_source(state: FSMContext, message: Message, telegram_id: int) -> None:
    render = await _render_current(telegram_id, state)
    await _show_panel(
        state=state,
        chat_id=message.chat.id,
        bot=message.bot,
        text=render.text,
        keyboard=render.keyboard,
        preferred_message=None,
    )


@router.message(Command("start"))
async def start(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await _register_user(message)
    await state.clear()
    await message.answer(
        "Привет! Я MedAlarm.\n\n"
        "Я напоминаю о приёме лекарств по вашему расписанию.\n"
        "Я не даю медицинских рекомендаций и не изменяю схему лечения.",
        reply_markup=open_menu_keyboard(),
    )
    await _delete_message_safe(message)


@router.message(Command("menu"))
@router.message(Command("add_medicine"))
@router.message(Command("my_medicines"))
@router.message(Command("today"))
@router.message(Command("history"))
@router.message(Command("settings"))
async def menu_alias(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await _register_user(message)
    command = (message.text or "").split()[0]
    if command == "/add_medicine":
        await state.update_data(add_draft={}, add_step="name")
        await _set_screen(state, SCREEN_MED_ADD)
    elif command == "/my_medicines":
        await _set_screen(state, SCREEN_MED_LIST)
    elif command == "/today":
        await _set_screen(state, SCREEN_TODAY)
    elif command == "/history":
        await state.update_data(history_period="week", history_medicine_id=None, history_page=0)
        await _set_screen(state, SCREEN_HISTORY)
    elif command == "/settings":
        await _set_screen(state, SCREEN_SETTINGS)
    else:
        await _set_screen(state, SCREEN_MENU)
    await state.update_data(awaiting_input=AWAIT_NONE)
    await _refresh_without_source(state, message, message.from_user.id)
    await _delete_message_safe(message)


@router.callback_query(F.data.startswith("ui:"))
async def ui_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user is None or callback.message is None or callback.data is None:
        return
    if callback.data == "ui:noop":
        await callback.answer()
        return

    await _register_user(callback)
    data = callback.data

    if data == "ui:menu":
        await state.update_data(awaiting_input=AWAIT_NONE)
        await _set_screen(state, SCREEN_MENU)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return
    if data == "ui:back":
        await state.update_data(awaiting_input=AWAIT_NONE)
        await _set_screen(state, SCREEN_MENU)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return

    if data == "ui:med:list":
        await state.update_data(awaiting_input=AWAIT_NONE)
        await _set_screen(state, SCREEN_MED_LIST)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return
    if data == "ui:med:add":
        await state.update_data(add_draft={}, add_step="name")
        await _set_screen(state, SCREEN_MED_ADD)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return
    if data.startswith("ui:med:view:"):
        medicine_id = int(data.split(":")[-1])
        await state.update_data(awaiting_input=AWAIT_NONE)
        await _set_screen(state, SCREEN_MED_VIEW, {"medicine_id": medicine_id})
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return
    if data.startswith("ui:med:toggle:"):
        medicine_id = int(data.split(":")[-1])
        async with session_scope() as session:
            user = await UserService.get_by_telegram_id(session, callback.from_user.id)
            if user is None:
                await callback.answer("Сначала выполните /start", show_alert=True)
                return
            medicine = await MedicineService.get_user_medicine(session, medicine_id, user.id)
            if medicine is None:
                await callback.answer("Лекарство не найдено", show_alert=True)
                return
            await MedicineService.set_medicine_active(session, medicine_id, user.id, not medicine.is_active)
        scheduler = get_scheduler()
        if scheduler:
            await scheduler.reload_jobs()
        await _set_screen(state, SCREEN_MED_VIEW, {"medicine_id": medicine_id})
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer("Статус обновлён")
        return
    if data.startswith("ui:med:delete:") and not data.startswith("ui:med:delete_confirm:"):
        medicine_id = int(data.split(":")[-1])
        async with session_scope() as session:
            user = await UserService.get_by_telegram_id(session, callback.from_user.id)
            if user is None:
                await callback.answer("Сначала выполните /start", show_alert=True)
                return
            medicines = await MedicineService.list_all_user_medicines(session, user.id)
        display_numbers = _build_display_number_map(medicines)
        medicine = next((item for item in medicines if item.id == medicine_id), None)
        if medicine is None:
            await callback.answer("Лекарство не найдено", show_alert=True)
            return
        await _show_panel(
            state=state,
            chat_id=callback.message.chat.id,
            bot=callback.bot,
            text=(
                f"Подтвердите удаление лекарства №{display_numbers[medicine.id]}.\n"
                "Будут удалены лекарство, расписания и история приёмов."
            ),
            keyboard=medicine_manage_keyboard(medicine_id, is_active=True, delete_confirm=True),
            preferred_message=callback.message,
        )
        await callback.answer()
        return
    if data.startswith("ui:med:delete_confirm:"):
        medicine_id = int(data.split(":")[-1])
        async with session_scope() as session:
            user = await UserService.get_by_telegram_id(session, callback.from_user.id)
            if user is None:
                await callback.answer("Сначала выполните /start", show_alert=True)
                return
            deleted = await MedicineService.hard_delete_medicine(session, medicine_id, user.id)
        if not deleted:
            await callback.answer("Лекарство не найдено", show_alert=True)
            return
        scheduler = get_scheduler()
        if scheduler:
            await scheduler.reload_jobs()
        await _set_screen(state, SCREEN_MED_LIST)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer("Удалено")
        return
    if data.startswith("ui:med:edit:"):
        medicine_id = int(data.split(":")[-1])
        await state.update_data(edit_medicine_id=medicine_id, awaiting_input=AWAIT_NONE)
        await _set_screen(state, SCREEN_MED_EDIT, {"medicine_id": medicine_id})
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return
    if data.startswith("ui:med:edit_field:"):
        _, _, _, medicine_id_raw, field = data.split(":")
        medicine_id = int(medicine_id_raw)
        await state.update_data(edit_medicine_id=medicine_id)
        prompts = {
            "name": ("Отправьте новое название.", AWAIT_EDIT_NAME),
            "dosage": ("Отправьте новую дозировку.", AWAIT_EDIT_DOSAGE),
            "times": ("Отправьте время (например 09:00, 14:00).", AWAIT_EDIT_TIMES),
            "days": ("Отправьте дни: * или 1,3,5 / пн,ср,пт.", AWAIT_EDIT_DAYS),
            "comment": ("Отправьте комментарий или '-'.", AWAIT_EDIT_COMMENT),
        }
        if field == "repeat":
            async with session_scope() as session:
                user = await UserService.get_by_telegram_id(session, callback.from_user.id)
                if user is None:
                    await callback.answer("Сначала выполните /start", show_alert=True)
                    return
                medicines = await MedicineService.list_all_user_medicines(session, user.id)
                medicine = await MedicineService.get_user_medicine(session, medicine_id, user.id)
                if medicine is None or not medicine.schedules:
                    await callback.answer("Лекарство не найдено", show_alert=True)
                    return
                current = medicine.schedules[0].remind_until_confirmed
                await MedicineService.update_schedule_fields(session, medicine, remind_until_confirmed=not current)
            scheduler = get_scheduler()
            if scheduler:
                await scheduler.reload_jobs()
            await _set_screen(state, SCREEN_MED_VIEW, {"medicine_id": medicine_id})
            await _refresh(state, callback.message, callback.from_user.id)
            await callback.answer("Повторы обновлены")
            return
        if field not in prompts:
            await callback.answer("Неизвестное поле", show_alert=True)
            return
        async with session_scope() as session:
            user = await UserService.get_by_telegram_id(session, callback.from_user.id)
            if user is None:
                await callback.answer("Сначала выполните /start", show_alert=True)
                return
            medicines = await MedicineService.list_all_user_medicines(session, user.id)
        display_numbers = _build_display_number_map(medicines)
        display_number = display_numbers.get(medicine_id)
        if display_number is None:
            await callback.answer("Лекарство не найдено", show_alert=True)
            return
        prompt, awaiting = prompts[field]
        await state.update_data(awaiting_input=awaiting)
        await _show_panel(
            state=state,
            chat_id=callback.message.chat.id,
            bot=callback.bot,
            text=f"Редактирование лекарства №{display_number}\n\n{prompt}",
            keyboard=medicine_edit_fields_keyboard(medicine_id),
            preferred_message=callback.message,
        )
        await callback.answer()
        return

    if data.startswith("ui:wizard:"):
        draft = await _state_get(state, "add_draft", {})
        step = await _state_get(state, "add_step", "name")
        if data == "ui:wizard:freq:daily":
            draft["frequency_mode"] = "daily"
            draft["days_of_week"] = "*"
            await state.update_data(add_draft=draft, add_step=_wizard_next_step("frequency", draft))
        elif data == "ui:wizard:freq:weekly":
            draft["frequency_mode"] = "weekly"
            draft.pop("days_of_week", None)
            await state.update_data(add_draft=draft, add_step=_wizard_next_step("frequency", draft))
        elif data == "ui:wizard:prev":
            await state.update_data(add_step=_wizard_prev_step(step, draft))
        elif data == "ui:wizard:next":
            if not _wizard_can_next(step, draft):
                await callback.answer("Сначала заполните текущий шаг", show_alert=True)
                return
            await state.update_data(add_step=_wizard_next_step(step, draft))
        elif data == "ui:wizard:save":
            if step != "confirm" or not _wizard_can_save(draft):
                await callback.answer("Форма заполнена не полностью", show_alert=True)
                return
            async with session_scope() as session:
                user = await UserService.get_by_telegram_id(session, callback.from_user.id)
                if user is None:
                    await callback.answer("Сначала выполните /start", show_alert=True)
                    return
                payload = MedicineCreatePayload(
                    name=draft["name"],
                    dosage_text=draft["dosage_text"],
                    times=list(draft["times"]),
                    days_of_week=draft["days_of_week"],
                    remind_until_confirmed=user.remind_until_confirmed,
                    snooze_minutes=user.default_snooze_minutes,
                    comment=draft.get("comment"),
                )
                await MedicineService.create_medicine_with_schedule(session, user, payload)
            scheduler = get_scheduler()
            if scheduler:
                await scheduler.reload_jobs()
            await state.update_data(add_draft={}, add_step="name", awaiting_input=AWAIT_NONE)
            await _set_screen(state, SCREEN_MED_LIST)
            await _refresh(state, callback.message, callback.from_user.id)
            await callback.answer("Сохранено")
            return
        await _set_screen(state, SCREEN_MED_ADD)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return

    if data == "ui:today":
        await state.update_data(awaiting_input=AWAIT_NONE)
        await _set_screen(state, SCREEN_TODAY)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return

    if data == "ui:history":
        await state.update_data(
            history_period="week",
            history_medicine_id=None,
            history_page=0,
            awaiting_input=AWAIT_NONE,
        )
        await _set_screen(state, SCREEN_HISTORY)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return
    if data.startswith("ui:history:period:"):
        await state.update_data(history_period=data.split(":")[-1], history_page=0)
        await _set_screen(state, SCREEN_HISTORY)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return
    if data == "ui:history:filter_med":
        await _set_screen(state, SCREEN_HISTORY_FILTER)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return
    if data.startswith("ui:history:medpick_page:"):
        await state.update_data(history_med_page=max(0, int(data.split(":")[-1])))
        await _set_screen(state, SCREEN_HISTORY_FILTER)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return
    if data.startswith("ui:history:med:"):
        value = data.split(":")[-1]
        await state.update_data(history_medicine_id=None if value == "all" else int(value), history_page=0)
        await _set_screen(state, SCREEN_HISTORY)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return
    if data.startswith("ui:history:page:"):
        await state.update_data(history_page=max(0, int(data.split(":")[-1])))
        await _set_screen(state, SCREEN_HISTORY)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return

    if data == "ui:settings":
        await state.update_data(awaiting_input=AWAIT_NONE)
        await _set_screen(state, SCREEN_SETTINGS)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer()
        return
    if data.startswith("ui:set:repeat:"):
        remind = data.endswith(":on")
        async with session_scope() as session:
            await UserService.update_repeat_mode(session, callback.from_user.id, remind)
        await _set_screen(state, SCREEN_SETTINGS)
        await _refresh(state, callback.message, callback.from_user.id)
        await callback.answer("Сохранено")
        return
    if data == "ui:set:tz":
        await state.update_data(awaiting_input=AWAIT_SET_TZ)
        await _show_panel(
            state=state,
            chat_id=callback.message.chat.id,
            bot=callback.bot,
            text="Отправьте новый timezone (например Europe/Kyiv).",
            keyboard=settings_keyboard(),
            preferred_message=callback.message,
        )
        await callback.answer()
        return
    if data == "ui:set:snooze":
        await state.update_data(awaiting_input=AWAIT_SET_SNOOZE)
        await _show_panel(
            state=state,
            chat_id=callback.message.chat.id,
            bot=callback.bot,
            text="Отправьте snooze в минутах (1-180).",
            keyboard=settings_keyboard(),
            preferred_message=callback.message,
        )
        await callback.answer()
        return

    await callback.answer()


@router.message(F.text)
async def text_router(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    awaiting = await _state_get(state, "awaiting_input", AWAIT_NONE)
    if not awaiting:
        return

    await _register_user(message)
    text = (message.text or "").strip()
    error: str | None = None

    try:
        if awaiting == AWAIT_ADD_NAME:
            if not text:
                raise ValueError("Название не может быть пустым.")
            draft = await _state_get(state, "add_draft", {})
            draft["name"] = text
            await state.update_data(add_draft=draft, add_step=_wizard_next_step("name", draft))
        elif awaiting == AWAIT_ADD_DOSAGE:
            if not text:
                raise ValueError("Дозировка не может быть пустой.")
            draft = await _state_get(state, "add_draft", {})
            draft["dosage_text"] = text
            await state.update_data(add_draft=draft, add_step=_wizard_next_step("dosage", draft))
        elif awaiting == AWAIT_ADD_TIMES:
            draft = await _state_get(state, "add_draft", {})
            draft["times"] = parse_times_input(text)
            await state.update_data(add_draft=draft, add_step=_wizard_next_step("times", draft))
        elif awaiting == AWAIT_ADD_DAYS:
            draft = await _state_get(state, "add_draft", {})
            draft["days_of_week"] = ",".join(str(day) for day in parse_days_input(text))
            await state.update_data(add_draft=draft, add_step=_wizard_next_step("days", draft))
        elif awaiting == AWAIT_ADD_COMMENT:
            draft = await _state_get(state, "add_draft", {})
            draft["comment"] = None if text == "-" else text
            await state.update_data(add_draft=draft, add_step=_wizard_next_step("comment", draft))
        elif awaiting in {AWAIT_EDIT_NAME, AWAIT_EDIT_DOSAGE, AWAIT_EDIT_TIMES, AWAIT_EDIT_DAYS, AWAIT_EDIT_COMMENT}:
            medicine_id = await _state_get(state, "edit_medicine_id")
            if not isinstance(medicine_id, int):
                raise ValueError("Контекст редактирования потерян.")
            async with session_scope() as session:
                user = await UserService.get_by_telegram_id(session, message.from_user.id)
                if user is None:
                    raise ValueError("Сначала выполните /start.")
                medicine = await MedicineService.get_user_medicine(session, medicine_id, user.id)
                if medicine is None:
                    raise ValueError("Лекарство не найдено.")
                if awaiting == AWAIT_EDIT_NAME:
                    await MedicineService.update_medicine_name(session, medicine, text)
                elif awaiting == AWAIT_EDIT_DOSAGE:
                    await MedicineService.update_medicine_dosage(session, medicine, text)
                elif awaiting == AWAIT_EDIT_TIMES:
                    await MedicineService.update_schedule_fields(session, medicine, times=parse_times_input(text))
                elif awaiting == AWAIT_EDIT_DAYS:
                    days = "*" if text == "*" else ",".join(str(day) for day in parse_days_input(text))
                    await MedicineService.update_schedule_fields(session, medicine, days_of_week=days)
                elif awaiting == AWAIT_EDIT_COMMENT:
                    await MedicineService.update_medicine_comment(session, medicine, None if text == "-" else text)
            scheduler = get_scheduler()
            if scheduler:
                await scheduler.reload_jobs()
            await _set_screen(state, SCREEN_MED_VIEW, {"medicine_id": medicine_id})
            await state.update_data(awaiting_input=AWAIT_NONE)
        elif awaiting == AWAIT_SET_TZ:
            if not validate_timezone(text):
                raise ValueError("Некорректный timezone. Пример: Europe/Kyiv.")
            async with session_scope() as session:
                user = await UserService.update_timezone(session, message.from_user.id, text)
                if user is None:
                    raise ValueError("Сначала выполните /start.")
            scheduler = get_scheduler()
            if scheduler:
                await scheduler.reload_jobs()
            await _set_screen(state, SCREEN_SETTINGS)
            await state.update_data(awaiting_input=AWAIT_NONE)
        elif awaiting == AWAIT_SET_SNOOZE:
            if not text.isdigit():
                raise ValueError("Введите целое число 1-180.")
            minutes = int(text)
            if minutes < 1 or minutes > 180:
                raise ValueError("Введите значение в диапазоне 1-180.")
            async with session_scope() as session:
                user = await UserService.update_snooze_minutes(session, message.from_user.id, minutes)
                if user is None:
                    raise ValueError("Сначала выполните /start.")
            await _set_screen(state, SCREEN_SETTINGS)
            await state.update_data(awaiting_input=AWAIT_NONE)
        else:
            raise ValueError("Неожиданный контекст ввода.")
    except ValueError as exc:
        error = str(exc)

    if error:
        current = await _render_current(message.from_user.id, state)
        await _show_panel(
            state=state,
            chat_id=message.chat.id,
            bot=message.bot,
            text=f"Ошибка: {error}\n\n{current.text}",
            keyboard=current.keyboard,
            preferred_message=None,
        )
    else:
        if awaiting.startswith("add_"):
            await _set_screen(state, SCREEN_MED_ADD)
        elif awaiting.startswith("edit_"):
            medicine_id = await _state_get(state, "edit_medicine_id")
            await _set_screen(state, SCREEN_MED_VIEW, {"medicine_id": medicine_id})
        await _refresh_without_source(state, message, message.from_user.id)

    try:
        await message.bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
    except Exception:
        pass
