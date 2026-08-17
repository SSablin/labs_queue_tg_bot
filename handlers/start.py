from aiogram import Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from states.start import Start

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message, dispatcher: Dispatcher, state: FSMContext) -> None:
    pool = dispatcher["pool"]
    if pool is None:
        await message.answer("Error: no connection with DB")

    if registered(): # TODO:: Write db call
        await message.answer(f"Hello, {name}!")
    else:
        await state.set_state(Start.waiting_for_auth)
        await message.answer("What's your name?")

@router.message(Start.waiting_for_auth)
async def input_name(message: types.Message, state: FSMContext, dispatcher: Dispatcher) -> None:
    pool = dispatcher["pool"]
    if pool is None:
        await message.answer("Error: no connection with DB")
    

