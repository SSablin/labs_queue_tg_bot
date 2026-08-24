import asyncio
import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from services import sheet_service
from states.start import Start
from utils.fsm import clear_fsm_logic

router = Router()
logger = logging.getLogger(__name__)


async def cancel_keyboard() -> types.InlineKeyboardMarkup:
    button = types.InlineKeyboardButton(text="cancel", callback_data="cancel_fsm")

    return types.InlineKeyboardMarkup(inline_keyboard=[[button]])


async def user_db_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    button = types.InlineKeyboardButton(
        text="Change name", callback_data=f"user_id:{user_id}"
    )

    return types.InlineKeyboardMarkup(inline_keyboard=[[button]])


async def records_keyboard(
    records: list[list[str]], action: str
) -> types.InlineKeyboardMarkup:
    buttons = []
    for cell in records:
        label = f"№{cell[0]}: {cell[1]} (lab.{cell[2]}) (st.{cell[3]})"
        try:
            row_number = int(cell[0])
        except Exception as e:
            logger.error(f"Row number is not integer: {e}")
            return

        callback_data = f"{action}:{cell[0]}"
        buttons.append(
            [types.InlineKeyboardButton(text=label, callback_data=callback_data)]
        )

    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "cancel_fsm")
async def cancel_callback_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    was_active = await clear_fsm_logic(state)

    if not callback.message:
        logger.error("no callback message")
        return

    if was_active:
        await callback.answer("Canceled")
    else:
        await callback.answer("Form has already filled or finished.", show_alert=True)
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception as e:
        logger.error(f"Failed to edit message: {e}")
        await callback.message.answer("Form canceled.")


@router.callback_query(F.data.startswith("user_id:"))
async def user_id_callback_handler(callback: types.CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    await state.set_state(Start.waiting_for_auth)

    if not callback.message:
        logger.error("No callback message")
        return

    await callback.message.edit_reply_markup(reply_markup=None)

    await state.update_data(is_name_change=True)

    keyboard = await cancel_keyboard()
    await callback.message.answer("Enter new name:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("remove:"))
@router.callback_query(F.data.startswith("done:"))
@router.callback_query(F.data.startswith("missed:"))
@router.callback_query(F.data.startswith("no:"))
async def active_callback(callback: types.CallbackQuery) -> None:
    await callback.answer()

    if not callback.message:
        logger.error("No callback message")
        return

    if not callback.data:
        logger.error("No callback data")
        callback.message.answer("The button is invalid")
        return

    value = callback.data.split(":", 1)[0]
    row_number = int(callback.data.split(":", 1)[1])
    col_number = 5

    try:
        await asyncio.to_thread(
            sheet_service.update_cell, 0, row_number, col_number, value
        )
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await callback.message.answer("Error writing to the table.")
        return

    try:
        await callback.message.edit_text(text=f"Status was updated to <b>{value}</b> for row #{row_number}.", reply_markup=None)
    except Exception as e:
        logger.error(f"Failed to edit message: {e}")
        await callback.message.answer("Form canceled.")
