from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.config import load_settings
from app.database.models import Medicine


def open_menu_keyboard(mini_app_url: str | None = None) -> InlineKeyboardMarkup:
    url = load_settings().mini_app_url if mini_app_url is None else mini_app_url
    rows: list[list[InlineKeyboardButton]] = []
    if url.startswith("https://"):
        rows.append([InlineKeyboardButton(text="💊 Открыть MedAlarm", web_app=WebAppInfo(url=url))])
    rows.append([InlineKeyboardButton(text="📋 Открыть меню", callback_data="ui:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💊 Лекарства", callback_data="ui:med:list")],
            [InlineKeyboardButton(text="📅 Сегодня", callback_data="ui:today")],
            [InlineKeyboardButton(text="📜 История", callback_data="ui:history")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="ui:settings")],
        ]
    )


def one_level_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️", callback_data="ui:back")]]
    )


def medicine_list_keyboard(
    medicines: list[Medicine],
    display_numbers: dict[int, int] | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="Добавить лекарство", callback_data="ui:med:add")]
    ]
    numbering = display_numbers or {}
    for medicine in medicines:
        display_number = numbering.get(medicine.id, medicine.id)
        rows.append(
            [InlineKeyboardButton(text=f"№{display_number}. {medicine.name}", callback_data=f"ui:med:view:{medicine.id}")]
        )
    rows.append([InlineKeyboardButton(text="⬅️", callback_data="ui:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def medicine_manage_keyboard(
    medicine_id: int,
    is_active: bool,
    *,
    delete_confirm: bool = False,
) -> InlineKeyboardMarkup:
    if delete_confirm:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Подтвердить удаление",
                        callback_data=f"ui:med:delete_confirm:{medicine_id}",
                    )
                ],
                [InlineKeyboardButton(text="К карточке", callback_data=f"ui:med:view:{medicine_id}")],
                [InlineKeyboardButton(text="В меню", callback_data="ui:menu")],
            ]
        )

    toggle_label = "Отключить" if is_active else "Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Изменить", callback_data=f"ui:med:edit:{medicine_id}"),
                InlineKeyboardButton(text=toggle_label, callback_data=f"ui:med:toggle:{medicine_id}"),
            ],
            [InlineKeyboardButton(text="Удалить", callback_data=f"ui:med:delete:{medicine_id}")],
            [
                InlineKeyboardButton(text="К списку", callback_data="ui:med:list"),
                InlineKeyboardButton(text="В меню", callback_data="ui:menu"),
            ],
        ]
    )


def medicine_edit_fields_keyboard(medicine_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Название", callback_data=f"ui:med:edit_field:{medicine_id}:name"),
                InlineKeyboardButton(text="Дозировка", callback_data=f"ui:med:edit_field:{medicine_id}:dosage"),
            ],
            [
                InlineKeyboardButton(text="Время", callback_data=f"ui:med:edit_field:{medicine_id}:times"),
                InlineKeyboardButton(text="Дни", callback_data=f"ui:med:edit_field:{medicine_id}:days"),
            ],
            [
                InlineKeyboardButton(text="Повторы", callback_data=f"ui:med:edit_field:{medicine_id}:repeat"),
                InlineKeyboardButton(text="Комментарий", callback_data=f"ui:med:edit_field:{medicine_id}:comment"),
            ],
            [
                InlineKeyboardButton(text="К карточке", callback_data=f"ui:med:view:{medicine_id}"),
                InlineKeyboardButton(text="В меню", callback_data="ui:menu"),
            ],
        ]
    )


def history_filter_keyboard(
    *,
    period: str = "week",
    page: int = 0,
    total_pages: int = 1,
    has_medicine_filter: bool = True,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=f"{'• ' if period == 'today' else ''}Сегодня",
                callback_data="ui:history:period:today",
            ),
            InlineKeyboardButton(
                text=f"{'• ' if period == 'week' else ''}Неделя",
                callback_data="ui:history:period:week",
            ),
            InlineKeyboardButton(
                text=f"{'• ' if period == 'month' else ''}Месяц",
                callback_data="ui:history:period:month",
            ),
        ]
    ]
    if has_medicine_filter:
        rows.append([InlineKeyboardButton(text="Фильтр по лекарству", callback_data="ui:history:filter_med")])
    if total_pages > 1:
        rows.append(
            [
                InlineKeyboardButton(text="◀", callback_data=f"ui:history:page:{max(0, page - 1)}"),
                InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ui:noop"),
                InlineKeyboardButton(text="▶", callback_data=f"ui:history:page:{min(total_pages - 1, page + 1)}"),
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️", callback_data="ui:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def history_medicine_filter_keyboard(
    medicines: list[Medicine],
    *,
    page: int,
    per_page: int = 10,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text="Все лекарства", callback_data="ui:history:med:all")]
    ]
    total_pages = max(1, (len(medicines) + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    part = medicines[page * per_page : page * per_page + per_page]
    for medicine in part:
        rows.append([InlineKeyboardButton(text=medicine.name, callback_data=f"ui:history:med:{medicine.id}")])
    if total_pages > 1:
        rows.append(
            [
                InlineKeyboardButton(text="◀", callback_data=f"ui:history:medpick_page:{max(0, page - 1)}"),
                InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="ui:noop"),
                InlineKeyboardButton(text="▶", callback_data=f"ui:history:medpick_page:{min(total_pages - 1, page + 1)}"),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(text="К истории", callback_data="ui:history"),
            InlineKeyboardButton(text="В меню", callback_data="ui:menu"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Часовой пояс", callback_data="ui:set:tz")],
            [InlineKeyboardButton(text="Snooze (мин)", callback_data="ui:set:snooze")],
            [
                InlineKeyboardButton(text="Повторы ON", callback_data="ui:set:repeat:on"),
                InlineKeyboardButton(text="Повторы OFF", callback_data="ui:set:repeat:off"),
            ],
            [InlineKeyboardButton(text="⬅️", callback_data="ui:back")],
        ]
    )


def medicine_wizard_keyboard(
    *,
    can_prev: bool,
    can_next: bool,
    can_save: bool,
    show_frequency: bool = False,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if show_frequency:
        rows.append(
            [
                InlineKeyboardButton(text="Каждый день", callback_data="ui:wizard:freq:daily"),
                InlineKeyboardButton(text="Конкретные дни", callback_data="ui:wizard:freq:weekly"),
            ]
        )
    nav_row: list[InlineKeyboardButton] = []
    if can_prev:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data="ui:wizard:prev"))
    if can_next:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data="ui:wizard:next"))
    if nav_row:
        rows.append(nav_row)
    if can_save:
        rows.append([InlineKeyboardButton(text="Сохранить", callback_data="ui:wizard:save")])
    rows.append(
        [
            InlineKeyboardButton(text="К списку", callback_data="ui:med:list"),
            InlineKeyboardButton(text="В меню", callback_data="ui:menu"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reminder_keyboard(medicine_id: int, schedule_id: int, scheduled_ts: int) -> InlineKeyboardMarkup:
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
                    text="⏰ Напомнить через 10 минут",
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
