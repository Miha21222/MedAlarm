from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    timezone = State()
    snooze = State()
    repeats = State()

