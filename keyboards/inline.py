import asyncio
import logging
import time
from datetime import datetime

from aiogram import Dispatcher, F, Router, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InputRichBlockTable,
    InputRichMessage,
    RichBlockTableCell,
    RichTextBold,
)

from constants.enums import QueueColumn, QueueStatus, WorksheetIndex
from services import sheet_service
from states.start import Start
from utils.fsm import clear_fsm_logic
from utils.input import input_name_from_db
from utils.sheet import run_sheet_operation

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
    records: list[list[str]],
    action: str,
    user_id: int | None = None,
    refresh_action: str | None = None,
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
    if refresh_action is not None:
        buttons.append(
            [
                types.InlineKeyboardButton(
                    text="Refresh",
                    callback_data=(
                        f"refresh_records:{refresh_action}:{int(time.time())}"
                    ),
                )
            ]
        )
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)


def own_queue_keyboard(
    records: list[list[str]], user_id: int
) -> types.InlineKeyboardMarkup:
    rows = []
    for cell in records:
        record_id = cell[4]
        label = f"№{cell[0]}: {cell[1]} (lab.{cell[2]})"
        rows.append(
            [
                types.InlineKeyboardButton(
                    text=f"{label} — сейчас",
                    callback_data=f"quick_time:{record_id}:{user_id}",
                ),
                types.InlineKeyboardButton(
                    text="done",
                    callback_data=f"quick_done:{record_id}:{user_id}",
                ),
            ]
        )
    return types.InlineKeyboardMarkup(inline_keyboard=rows)


def get_current_sheet_datetime() -> tuple[str, str]:
    now = datetime.now()
    return now.strftime("%d.%m.%Y"), now.strftime("%H:%M:%S")


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
async def remove_callback(
    callback: types.CallbackQuery, dispatcher: Dispatcher
) -> None:
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
        record = await asyncio.to_thread(
            sheet_service.get_record_by_id, WorksheetIndex.QUEUE, record_id
        )
        if not record:
            await callback.answer("This is not your record.", show_alert=True)
            return
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
@router.callback_query(F.data.startswith("self_done:"))
@router.callback_query(F.data.startswith("missed:"))
@router.callback_query(F.data.startswith("no:"))
async def action_callback(
    callback: types.CallbackQuery, dispatcher: Dispatcher
) -> None:
    if not isinstance(callback.message, types.Message):
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

    record = None
    if action in ("done", "self_done"):
        try:
            record = await asyncio.to_thread(
                sheet_service.get_record_by_id, WorksheetIndex.QUEUE, record_id
            )
        except Exception:
            logger.exception("Sheet error while checking record state")
            await callback.message.answer("Error checking record.")
            return
        if not record:
            await callback.answer("Record not found.", show_alert=True)
            await callback.message.edit_reply_markup(reply_markup=None)
            return
        if record.get("Was?") != QueueStatus.ACTIVE.value:
            await callback.answer("This record is no longer active.", show_alert=True)
            await callback.message.edit_reply_markup(reply_markup=None)
            return

    update_status = QueueStatus.DONE.value if action == "self_done" else action

    if update_status == QueueStatus.DONE.value:
        current_date, current_time = get_current_sheet_datetime()
        try:
            result = await asyncio.to_thread(
                sheet_service.complete_record_by_id,
                WorksheetIndex.QUEUE,
                record_id,
                current_date,
                current_time,
            )
            if result == "not_found":
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.answer("Record not found.")
                return
            if result == "inactive":
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.answer(
                    "This record is no longer active.", show_alert=True
                )
                return
        except Exception:
            logger.exception("Sheet error while completing record")
            await callback.message.answer("Error updating record.")
            return
    else:
        try:
            updated = await asyncio.to_thread(
                sheet_service.update_cell_by_id,
                WorksheetIndex.QUEUE,
                record_id,
                QueueColumn.WAS,
                update_status,
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
            f"Status was updated to <b>{update_status}</b>.",
            reply_markup=None,
            parse_mode="HTML",
        )
        await callback.answer("Updated")
    except TelegramBadRequest:
        await callback.answer("Failed to edit the message")
        await callback.message.answer(
            f"Status was updated to <b>{update_status}</b>.",
            parse_mode="HTML",
        )


@router.callback_query(F.data.startswith("quick_time:"))
@router.callback_query(F.data.startswith("quick_done:"))
async def quick_record_action_callback(
    callback: types.CallbackQuery, dispatcher: Dispatcher
) -> None:
    if not callback.message or not callback.data or not callback.from_user:
        logger.error("Invalid quick record callback")
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Invalid button data.", show_alert=True)
        return

    action, record_id, user_id_str = parts
    try:
        button_user_id = int(user_id_str)
    except ValueError:
        await callback.answer("Invalid button data.", show_alert=True)
        return
    if button_user_id != callback.from_user.id:
        await callback.answer("You cannot do that.", show_alert=True)
        return

    input_name = await input_name_from_db(callback.message, dispatcher)
    if not input_name:
        return

    try:
        record = await asyncio.to_thread(
            sheet_service.get_record_by_id, WorksheetIndex.QUEUE, record_id
        )
        if not record:
            await callback.answer("Record not found.", show_alert=True)
            await callback.message.edit_reply_markup(reply_markup=None)
            return
        if record.get("Name") != input_name:
            await callback.answer("This is not your record.", show_alert=True)
            return

        current_date, current_time = get_current_sheet_datetime()
        if action == "quick_time":
            updates = [
                (QueueColumn.DATE, current_date),
                (QueueColumn.TIME, current_time),
            ]
        elif action == "quick_done":
            if record.get("Was?") != QueueStatus.ACTIVE.value:
                await callback.answer(
                    "This record is no longer active.", show_alert=True
                )
                await callback.message.edit_reply_markup(reply_markup=None)
                return
            result = await asyncio.to_thread(
                sheet_service.complete_record_by_id,
                WorksheetIndex.QUEUE,
                record_id,
                current_date,
                current_time,
            )
            if result == "not_found":
                await callback.answer("Record not found.", show_alert=True)
                return
            if result == "inactive":
                await callback.answer(
                    "This record is no longer active.", show_alert=True
                )
                await callback.message.edit_reply_markup(reply_markup=None)
                return
            updates = []
        else:
            await callback.answer("Invalid button data.", show_alert=True)
            return

        for column, value in updates:
            updated = await asyncio.to_thread(
                sheet_service.update_cell_by_id,
                WorksheetIndex.QUEUE,
                record_id,
                column,
                value,
            )
            if not updated:
                await callback.answer("Record not found.", show_alert=True)
                return
    except Exception:
        logger.exception("Sheet error while applying quick record action")
        await callback.message.answer("Error updating record.")
        return

    await callback.answer("Updated")
    await callback.message.edit_reply_markup(reply_markup=None)


@router.callback_query(F.data.startswith("refresh_queue:"))
async def refresh_queue_callback(callback: types.CallbackQuery) -> None:
    if not callback.message:
        logger.error("No callback message")
        return

    if not callback.data:
        logger.error("No callback data")
        await callback.message.answer("The button is invalid")
        return

    parts = callback.data.split(":")
    if len(parts) != 2:
        await callback.answer("Invalid button data.", show_alert=True)
        return

    try:
        ts = int(parts[1])
    except ValueError:
        await callback.answer("Invalid button data.", show_alert=True)
        return

    now = int(time.time())
    # timeout is 60 seconds
    if now - ts > 60:
        await callback.answer("Button expired.", show_alert=True)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            logger.exception("Failed to remove expired button")
        return

    # regenerate and send updated table (attach a fresh refresh button)
    result = await run_sheet_operation(
        callback.message, sheet_service.sort, worksheet_index=WorksheetIndex.QUEUE
    )
    if result is None:
        return

    data = await run_sheet_operation(
        callback.message,
        sheet_service.get_queue,
        WorksheetIndex.QUEUE,
        QueueStatus.ACTIVE.value,
    )
    if data is None:
        return
    if len(data) <= 1:
        await callback.message.answer("Queue is empty")
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:
            logger.exception("Failed to remove old button")
        await callback.answer("Queue is empty.")
        return

    table_grid = []

    for item in data:
        if not table_grid:
            row_cells = [
                RichBlockTableCell(
                    text=RichTextBold(text=header), align="center", valign="middle"
                )
                for header in item
            ]
        else:
            row_cells = [
                RichBlockTableCell(text=cell, align="left", valign="middle")
                for cell in item
            ]
        table_grid.append(row_cells)

    table_block = InputRichBlockTable(
        cells=table_grid, is_bordered=True, is_striped=True
    )
    rich_message = InputRichMessage(blocks=[table_block])

    new_ts = int(time.time())
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Refresh", callback_data=f"refresh_queue:{new_ts}"
                )
            ]
        ]
    )

    try:
        await callback.message.answer_rich(
            rich_message=rich_message, reply_markup=keyboard
        )
    except Exception:
        logger.exception("Failed to send refreshed table")
        await callback.message.answer("Failed to send refreshed table.")
        return

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        logger.exception("Failed to remove old button")
    await callback.answer("Queue refreshed.")


@router.callback_query(F.data.startswith("refresh_records:"))
async def refresh_records_callback(
    callback: types.CallbackQuery, dispatcher: Dispatcher
) -> None:
    if not callback.message or not callback.data or not callback.from_user:
        logger.error("Invalid records refresh callback")
        return

    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Invalid button data.", show_alert=True)
        return

    _, view, timestamp = parts
    try:
        if int(time.time()) - int(timestamp) > 60:
            await callback.answer("Button expired.", show_alert=True)
            await callback.message.edit_reply_markup(reply_markup=None)
            return
    except ValueError:
        await callback.answer("Invalid button data.", show_alert=True)
        return

    try:
        await asyncio.to_thread(sheet_service.sort, WorksheetIndex.QUEUE)
        input_name = None
        if view in {"remove", "self_done", "again", "self_no"}:
            input_name = await input_name_from_db(callback.message, dispatcher)
            if not input_name:
                return

        if view == "remove":
            records = await asyncio.to_thread(
                sheet_service.find_records, WorksheetIndex.QUEUE, input_name
            )
            action = "remove"
        elif view == "done":
            records = await asyncio.to_thread(
                sheet_service.get_queue_records,
                WorksheetIndex.QUEUE,
                QueueStatus.ACTIVE.value,
            )
            action = "done"
        elif view == "self_done":
            records = await asyncio.to_thread(
                sheet_service.get_queue_records,
                WorksheetIndex.QUEUE,
                QueueStatus.ACTIVE.value,
                None,
                input_name,
            )
            action = "self_done"
        elif view == "missed":
            records = await asyncio.to_thread(
                sheet_service.get_queue_records,
                WorksheetIndex.QUEUE,
                QueueStatus.ACTIVE.value,
            )
            action = "missed"
        elif view == "no":
            records = await asyncio.to_thread(
                sheet_service.get_queue_records,
                WorksheetIndex.QUEUE,
                None,
                QueueStatus.ACTIVE.value,
            )
            action = QueueStatus.ACTIVE.value
        elif view == "again":
            records = await asyncio.to_thread(
                sheet_service.get_queue_records,
                WorksheetIndex.QUEUE,
                QueueStatus.DONE.value,
                None,
                input_name,
            )
            action = QueueStatus.ACTIVE.value
        elif view == "self_no":
            records = await asyncio.to_thread(
                sheet_service.get_queue_records,
                WorksheetIndex.QUEUE,
                None,
                QueueStatus.ACTIVE.value,
                input_name,
            )
            action = QueueStatus.ACTIVE.value
        else:
            await callback.answer("Invalid button data.", show_alert=True)
            return

        if not records:
            await callback.answer("No records found.", show_alert=True)
            await callback.message.edit_reply_markup(reply_markup=None)
            return

        keyboard = records_keyboard(
            records,
            action,
            callback.from_user.id,
            refresh_action=view,
        )
        await callback.message.edit_reply_markup(reply_markup=keyboard)
        await callback.answer("List refreshed.")
    except Exception:
        logger.exception("Error while refreshing records list: %s", view)
        await callback.message.answer("Failed to refresh records.")
