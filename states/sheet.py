from aiogram.fsm.state import State, StatesGroup


class Add(StatesGroup):
    waiting_for_lab = State()
    waiting_for_date = State()
    waiting_for_time = State()


class Cheat(StatesGroup):
    waiting_for_lab = State()
    waiting_for_cheat = State()
