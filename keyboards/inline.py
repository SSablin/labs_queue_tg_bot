import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

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


@router.callback_query(F.data == "cancel_fsm")
async def cancel_callback_handler(callback: types.CallbackQuery, state: FSMContext):
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
async def user_id_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Start.waiting_for_auth)

    if not callback.message:
        logger.error("no callback message")
        return

    await state.update_data(is_name_change=True)
    keyboard = await cancel_keyboard()
    await callback.message.answer("Enter new name:", reply_markup=keyboard)
