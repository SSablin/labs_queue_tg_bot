import logging

from aiogram import Dispatcher, F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import upsert_user
from keyboards.inline import cancel_keyboard, user_db_keyboard
from states.start import Start
from utils.fsm import clear_fsm_logic
from utils.input import input_name_from_db

router = Router()

logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(
    message: types.Message, state: FSMContext, dispatcher: Dispatcher
) -> None:
    input_name = await input_name_from_db(message, dispatcher)
    if not input_name:
        return

    if not message.from_user:
        await message.answer("Failed to get user_id")
        return

    if input_name is not None:
        keyboard = await user_db_keyboard(message.from_user.id)
        await message.answer(f"Hello, {input_name}!", reply_markup=keyboard)
    else:
        await state.set_state(Start.waiting_for_auth)
        keyboard = await cancel_keyboard()
        await message.answer("What is your name?", reply_markup=keyboard)


@router.message(Command("cancel"))
@router.message(F.text.casefold() == "cancel")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    """
    Allow user to cancel any action
    """
    was_active = await clear_fsm_logic(state)

    if was_active:
        await message.answer(
            "Cancelled.",
            reply_markup=types.ReplyKeyboardRemove(),
        )
    else:
        await message.answer("You are not filling now.")


@router.message(Command("edit_profile"))
async def cmd_edit_profile(message: types.Message, state: FSMContext):
    await state.set_state(Start.waiting_for_auth)

    await state.update_data(is_name_change=True)
    keyboard = await cancel_keyboard()
    await message.answer("Enter new name:", reply_markup=keyboard)


@router.message(Start.waiting_for_auth)
async def input_name(
    message: types.Message, state: FSMContext, dispatcher: Dispatcher
) -> None:
    pool = dispatcher["pool"]
    if pool is None:
        logger.error("DB error")
        await message.answer("Error: no connection with DB")
        return

    input_name = message.text
    if not input_name:
        await message.answer("Name can not be empty. Try again.")
        return

    if not message.from_user:
        await message.answer("Failed to get user_id")
        return

    try:
        await upsert_user(
            pool,
            message.from_user.id,
            message.from_user.username,
            message.from_user.full_name,
            input_name,
        )
    except Exception as e:
        logger.error(f"UPSERT error: {e}")
        await message.answer("Connection error")
        return

    keyboard = await user_db_keyboard(message.from_user.id)
    data = await state.get_data()
    if data.get("is_name_change"):
        msg = "Name updated successfully!"
        logger.info(
            f"User {message.from_user.id} succesfully updated name: {input_name}"
        )
    else:
        msg = f"Your name in table is {input_name}!"
        logger.info(
            f"User {message.from_user.id} succesfully added to db, name: {input_name}"
        )

    await message.answer(msg, reply_markup=keyboard)

    await state.clear()


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = """
<b>Commands</b>
/start
/edit_profile
/cancel
/help
/sheet
/queue
/add
/cheat
/remove
/done
/missed
/recover
/rebirth
"""
    await message.answer(text=text, parse_mode="HTML")
