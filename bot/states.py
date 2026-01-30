from aiogram.fsm.state import State, StatesGroup

class ReminderStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_time = State()
    waiting_for_repeat = State()
    waiting_for_timezone = State()
    editing_message = State()
    editing_time = State()
    editing_repeat = State()