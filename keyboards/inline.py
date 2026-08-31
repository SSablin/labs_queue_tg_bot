import asyncio
import logging

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from constants.enums import QueueColumn, WorksheetIndex
from services import sheet_service
from states.start import Start
from utils.fsm import clear_fsm_logic

router = Router()
logger = logging.getLogger(__name__)


def cancel_keyboard() -> types.InlineKeyboardMarkup:
    button = types.InlineKeyboardButton(text="cancel", callback_data="cancel_fsm")

    return types.InlineKeyboardMarkup(inline_keyboard=[[button]])


def user_db_keyboard(user_id: int) -> types.InlineKeyboardMarkup:
    button = types.InlineKeyboardButton(
        text="Change name", callback_data=f"user_id:{user_id}"
    )

    return types.InlineKeyboardMarkup(inline_keyboard=[[button]])


def records_keyboard(
    records: list[list[str]], action: str, user_id: int | None = None
) -> types.InlineKeyboardMarkup:
    buttons = []
    for cell in records:
        # cell = [№, Name, Lab, Was?, record_id]
        label = f"№{cell[0]}: {cell[1]} (lab.{cell[2]}) (st.{cell[3]})"
        record_id = cell[4]  # UUID
        data = f"{action}:{record_id}"
        if user_id is not None:
            data += f":{user_id}"
        buttons.append([types.InlineKeyboardButton(text=label, callback_data=data)])
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "cancel_fsm")
async def cancel_callback_handler(
    callback: types.CallbackQuery, state: FSMContext
) -> None:
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
    except Exception:
        logger.exception("Failed to edit message")
        await callback.message.answer("Form canceled.")


@router.callback_query(F.data.startswith("user_id:"))
async def user_id_callback_handler(
    callback: types.CallbackQuery, state: FSMContext
) -> None:
    await callback.answer()
    await state.set_state(Start.waiting_for_auth)

    if not callback.message:
        logger.error("No callback message")
        return

    await callback.message.edit_reply_markup(reply_markup=None)

    await state.update_data(is_name_change=True)

    keyboard = cancel_keyboard()
    await callback.message.answer("Enter new name:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("remove:"))
async def remove_callback(callback: types.CallbackQuery) -> None:
    await callback.answer()
    if not callback.message:
        logger.error("No callback message")
        return
    if not callback.data:
        logger.error("No callback data")
        await callback.message.answer("The button is invalid")
        return

    parts = callback.data.split(":")
    if len(parts) == 3:
        action, record_id, user_id_str = parts
        try:
            callback_user_id = int(user_id_str)
        except ValueError:
            await callback.answer("Invalid button data.", show_alert=True)
            return
        if callback_user_id != callback.from_user.id:
            await callback.answer("You cannot do that.", show_alert=True)
            return
    else:
        await callback.answer("Invalid button data.", show_alert=True)
        return

    try:
        deleted = await asyncio.to_thread(
            sheet_service.delete_record_by_id, WorksheetIndex.QUEUE, record_id
        )
        if not deleted:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Record not found or already removed.")
            return
    except Exception:
        logger.exception("Sheet error while deleting record")
        await callback.message.answer("Error deleting record.")
        return

    await callback.message.edit_text(
        "Record removed.",
        reply_markup=None,
    )
    await callback.answer("Removed")


@router.callback_query(F.data.startswith("done:"))
@router.callback_query(F.data.startswith("missed:"))
@router.callback_query(F.data.startswith("no:"))
async def action_callback(callback: types.CallbackQuery) -> None:
    await callback.answer()

    if not callback.message:
        logger.error("No callback message")
        return

    if not callback.data:
        logger.error("No callback data")
        await callback.message.answer("The button is invalid")
        return

    parts = callback.data.split(":")
    if len(parts) == 3:
        action, record_id, user_id_str = parts
        try:
            callback_user_id = int(user_id_str)
        except ValueError:
            await callback.answer("Invalid button data.", show_alert=True)
            return
        if callback_user_id != callback.from_user.id:
            await callback.answer("You cannot do that.", show_alert=True)
            return
    else:
        await callback.answer("Invalid button data.", show_alert=True)
        return

    try:
        updated = await asyncio.to_thread(
            sheet_service.update_cell_by_id,
            WorksheetIndex.QUEUE,
            record_id,
            QueueColumn.WAS,
            action,
        )
        if not updated:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.answer("Record not found.")
            return
    except Exception:
        logger.exception("Sheet error while updating record")
        await callback.message.answer("Error updating record.")
        return

    try:
        await callback.message.edit_text(
            f"Status was updated to <b>{action}</b>.",
            reply_markup=None,
            parse_mode="HTML",
        )
    except Exception as e:
        await callback.answer("Failed to edit the message")
        await callback.message.answer(
            f"Status was updated to <b>{action}</b>.",
            parse_mode="HTML",
        )
