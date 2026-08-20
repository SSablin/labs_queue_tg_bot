import logging

from aiogram import Dispatcher, F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from database.db import upsert_user
from database.session_manager import get_user
from keyboards.inline import user_db_keyboard
from states.start import Start

router = Router()

logger = logging.getLogger(__name__)


@router.message(Command("start"))
async def cmd_start(
    message: types.Message, state: FSMContext, dispatcher: Dispatcher
) -> None:
    pool = dispatcher["pool"]
    if pool is None:
        await message.answer("Error: no connection with DB")
        return

    if not message.from_user:
        await message.answer("Failed to get user_id")
        return

    try:
        input_name = await get_user(pool, message.from_user.id)
    except Exception as e:
        logger.error(f"DB error: {e}")
        await message.answer("Database error")
        return

    if input_name is not None:
        keyboard = await user_db_keyboard(message.from_user.id)
        await message.answer(f"Hello, {input_name}!", reply_markup=keyboard)
    else:
        await state.set_state(Start.waiting_for_auth)
        await message.answer("What is your name?")


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

    await message.answer(
        msg, reply_markup=keyboard
    )

    await state.clear()


@router.message(Command("cancel"))
@router.message(F.text == "cancel")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    """
    Allow user to cancel any action
    """
    current_state = await state.get_state()
    if current_state is None:
        return

    logger.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer(
        "Cancelled.",
        reply_markup=types.ReplyKeyboardRemove(),
    )
