from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def medicine_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сохранить", callback_data="medicine_save"),
                InlineKeyboardButton(text="Изменить", callback_data="medicine_edit"),
                InlineKeyboardButton(text="Отмена", callback_data="medicine_cancel"),
            ]
        ]
    )


def medicine_manage_keyboard(medicine_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle_label = "Отключить" if is_active else "Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=toggle_label, callback_data=f"med_toggle:{medicine_id}"),
                InlineKeyboardButton(text="Удалить", callback_data=f"med_delete:{medicine_id}"),
            ]
        ]
    )


def medicine_delete_confirm_keyboard(medicine_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, удалить полностью", callback_data=f"med_delete_confirm:{medicine_id}"),
            ],
            [
                InlineKeyboardButton(text="Отмена", callback_data=f"med_delete_cancel:{medicine_id}"),
            ],
        ]
    )


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


def settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Часовой пояс", callback_data="settings_tz")],
            [InlineKeyboardButton(text="Snooze (мин)", callback_data="settings_snooze")],
            [InlineKeyboardButton(text="Повторы до подтверждения", callback_data="settings_repeat")],
        ]
    )
