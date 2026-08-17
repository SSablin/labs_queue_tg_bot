from aiogram.fsm.state import State, StatesGroup


class Start(StatesGroup):
    waiting_for_auth = State()
