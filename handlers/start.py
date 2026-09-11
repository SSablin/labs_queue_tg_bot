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
    if not message.from_user:
        await message.answer("Failed to get user_id")
        return

    input_name = await input_name_from_db(message, dispatcher)
    if input_name:
        keyboard = user_db_keyboard(message.from_user.id)
        await message.answer(f"Hello, {input_name}!", reply_markup=keyboard)
    else:
        await state.set_state(Start.waiting_for_auth)
        keyboard = cancel_keyboard()
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
        await message.answer("You are not filling anything right now.")


@router.message(Command("edit_profile"))
async def cmd_edit_profile(message: types.Message, state: FSMContext) -> None:
    await state.set_state(Start.waiting_for_auth)

    await state.update_data(is_name_change=True)
    keyboard = cancel_keyboard()
    await message.answer("Enter new name:", reply_markup=keyboard)


@router.message(Start.waiting_for_auth)
async def input_name(
    message: types.Message, state: FSMContext, dispatcher: Dispatcher
) -> None:
    pool = dispatcher.get("pool")
    if not pool:
        logger.error("DB error: dispatcher has no 'pool' configured")
        await message.answer("Error: no connection to DB")
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
    except Exception:
        logger.exception("UPSERT error while saving user %s", message.from_user.id)
        await message.answer("Connection error")
        return

    keyboard = user_db_keyboard(message.from_user.id)
    data = await state.get_data()
    if data.get("is_name_change"):
        msg = "Name updated successfully!"
        logger.info("User %s successfully updated name: %s", message.from_user.id, input_name)
    else:
        msg = f"Your name in table is {input_name}!"
        logger.info("User %s successfully added to db, name: %s", message.from_user.id, input_name)

    await message.answer(msg, reply_markup=keyboard)
    await state.clear()


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    text = """
<b>Bot help</b>

<b>1. Profile and setup</b>
• /start — start working with the bot. If your name is already saved, the bot greets you; otherwise it asks for your name.
• /edit_profile — update the saved name.
• /cancel — cancel the current prompt and return to the previous state.

<b>2. Queue actions</b>
• /queue — open the current queue and sort records.
• /add — create a new queue record step by step: lab number, date, and time.
• /remove — select a queue record from the list and remove it.
• /done — select a queue record and mark it as done.
• /missed — select a queue record and mark it as missed.
• /recover — select a finished or missed record and return it to the active queue.
• /again — select your own completed record and return it to the active queue.
• /cheat — create a cheat record step by step.
• /rebirth — reset your own record status back to active ("no").

<b>3. Sheet and utilities</b>
• /sheet — open the Google Sheet link.
• /source — open the project source link.
• /help — show this help again.

<b>4. How it works</b>
• Most commands do not take direct arguments in the message text.
• Instead, the bot asks for the needed data or shows a selection list.
• If the bot asks you to enter text, just send it. Use /cancel to abort at any time.
"""
    await message.answer(text=text, parse_mode="HTML")


@router.message(Command("source"))
async def cmd_source(message: types.Message):
    text = """
<b>github</b>
<a href="https://github.com/SSablin/labs_queue_tg_bot">source</a>
"""
    await message.answer(
        text,
        parse_mode="HTML",
        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
    )
