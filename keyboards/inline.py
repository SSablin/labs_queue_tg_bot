import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from states.start import Start

router = Router()
logger = logging.getLogger(__name__)


async def user_db_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    button = types.InlineKeyboardButton(
        text="Change name", callback_data=f"user_id:{user_id}"
    )

    return types.InlineKeyboardMarkup(inline_keyboard=[[button]])


async def cancel_keyboard() -> types.InlineKeyboardMarkup:
    button = types.InlineKeyboardButton(text="cancel", switch_inline_query="cancel")

    return types.InlineKeyboardMarkup(inline_keyboard=[[button]])


@router.callback_query(F.data.startswith("user_id:"))
async def user_id_callback(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Start.waiting_for_auth)

    if not callback.message:
        logger.error("no callback message")
        return

    await state.update_data(is_name_change=True)
    await callback.message.answer("Enter new name:")
