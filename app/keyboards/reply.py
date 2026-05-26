from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def frequency_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Каждый день")],
            [KeyboardButton(text="Конкретные дни недели")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def repeat_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Да"), KeyboardButton(text="Нет")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def settings_repeat_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="on"), KeyboardButton(text="off")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

