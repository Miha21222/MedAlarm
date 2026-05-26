from aiogram.fsm.state import State, StatesGroup


class AddMedicineStates(StatesGroup):
    name = State()
    dosage = State()
    time = State()
    frequency = State()
    days = State()
    repeat = State()
    comment = State()
    confirm = State()

