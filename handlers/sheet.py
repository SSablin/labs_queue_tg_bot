import logging
import re

from aiogram import Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InputRichBlockTable,
    InputRichMessage,
    RichBlockTableCell,
    RichTextBold,
)

from constants.enums import QueueStatus, WorksheetIndex
from keyboards.inline import cancel_keyboard, own_queue_keyboard, records_keyboard
from services import sheet_service
from states.sheet import Add, Cheat, Add_oneline
from utils.input import input_name_from_db, parse_date, parse_lab
from utils.sheet import run_sheet_operation
from config import SHEET_URL

router = Router()

logger = logging.getLogger(__name__)


@router.message(Command("queue"))
async def cmd_queue(message: types.Message, dispatcher: Dispatcher) -> None:
    result = await run_sheet_operation(
        message, sheet_service.sort, worksheet_index=WorksheetIndex.QUEUE
    )
    if result is None:
        return

    data = await run_sheet_operation(
        message,
        sheet_service.get_queue,
        WorksheetIndex.QUEUE,
        QueueStatus.ACTIVE.value,
    )
    if data is None:
        return
    if not data:
        await message.answer("Queue is empty")
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

    # attach a refresh button that is valid for 1 minute
    import time

    ts = int(time.time())
    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [
                types.InlineKeyboardButton(
                    text="Refresh", callback_data=f"refresh_queue:{ts}"
                )
            ]
        ]
    )

    input_name = await input_name_from_db(message, dispatcher)
    if input_name and message.from_user:
        own_records = await run_sheet_operation(
            message,
            sheet_service.get_queue_records,
            worksheet_index=WorksheetIndex.QUEUE,
            was=QueueStatus.ACTIVE.value,
            input_name=input_name,
        )
        if own_records:
            keyboard.inline_keyboard.extend(
                own_queue_keyboard(own_records, message.from_user.id).inline_keyboard
            )

    await message.answer_rich(rich_message=rich_message, reply_markup=keyboard)


@router.message(Command("add_oneline"))
async def cmd_add_oneline(
    message: types.Message, dispatcher: Dispatcher, state: FSMContext
):
    input_name = await input_name_from_db(message, dispatcher)
    if not input_name:
        return

    await state.update_data(input_name=input_name)

    await state.set_state(Add_oneline.waiting_for_lab)

    keyboard = cancel_keyboard()
    await message.answer("Please, send one line date", reply_markup=keyboard)


@router.message(Add_oneline.waiting_for_lab)
async def input_lab_one_line(message: types.Message, state: FSMContext) -> None:
    lab = await parse_lab(message)
    if lab is None:
        return

    await state.update_data(lab=lab)

    if not message.from_user:
        await message.answer("Failed to get user_id")
        return

    await state.set_state(Add_oneline.waiting_for_date)
    keyboard = cancel_keyboard()
    await message.answer("Which date?", reply_markup=keyboard)


@router.message(Add_oneline.waiting_for_date)
async def on_input_one_line_text(message: types.Message, state: FSMContext):
    date = await parse_date(message)
    if date is None:
        return

    data = await state.get_data()
    input_name = data.get("input_name")
    lab = data.get("lab")

    record = [input_name, date["date"], date["time"], lab, QueueStatus.ACTIVE.value]

    result = await run_sheet_operation(
        message,
        sheet_service.add_record,
        worksheet_index=WorksheetIndex.QUEUE,
        record=record,
        add_uuid=True,
    )
    if result is None:
        return

    await message.answer(f"New record: {date}")
    await state.clear()

    result = await run_sheet_operation(
        message, sheet_service.sort, worksheet_index=WorksheetIndex.QUEUE
    )
    if result is None:
        return


@router.message(Command("add"))
async def cmd_add(
    message: types.Message, dispatcher: Dispatcher, state: FSMContext
) -> None:
    # TODO: add gitlab format input, add button

    input_name = await input_name_from_db(message, dispatcher)
    if not input_name:
        return

    await state.update_data(input_name=input_name)

    await state.set_state(Add.waiting_for_lab)

    keyboard = cancel_keyboard()
    await message.answer("Which lab?", reply_markup=keyboard)


@router.message(Add.waiting_for_lab)
async def input_lab(message: types.Message, state: FSMContext) -> None:
    lab = await parse_lab(message)
    if lab is None:
        return

    await state.update_data(lab=lab)

    if not message.from_user:
        await message.answer("Failed to get user_id")
        return

    await state.set_state(Add.waiting_for_date)
    keyboard = cancel_keyboard()
    await message.answer("Which date?", reply_markup=keyboard)


@router.message(Add.waiting_for_date)
async def input_date(message: types.Message, state: FSMContext) -> None:
    input_date = message.text
    if not input_date:
        await message.answer("Data can not be empty. Try again.")
        return

    pattern = r"^(0?[1-9]|[12][0-9]|3[01])\.(0?[1-9]|1[0-2])(\.\d{4}|\.\d{2})?$"
    if not re.fullmatch(pattern, input_date):
        await message.answer(
            "Date is incorrect. Send date in format: [D]D.[M]M[.[YY]YY]"
        )
        return

    await state.update_data(date=input_date)

    await state.set_state(Add.waiting_for_time)

    keyboard = cancel_keyboard()
    await message.answer("Which time?", reply_markup=keyboard)


@router.message(Add.waiting_for_time)
async def input_time(message: types.Message, state: FSMContext) -> None:
    input_time = message.text
    if not input_time:
        await message.answer("Time can not be empty. Try again")
        return

    pattern = r"^(0?\d|1\d|2[0-3]):[0-5]\d(:[0-5]\d)?$"
    if not re.fullmatch(pattern, input_time):
        await message.answer("Time is incorrect. Send time in format: [H]H:MM[:SS]")
        return

    data = await state.get_data()
    input_name = data.get("input_name")
    lab = data.get("lab")
    date = data.get("date")

    record = [input_name, date, input_time, lab, QueueStatus.ACTIVE.value]

    result = await run_sheet_operation(
        message,
        sheet_service.add_record,
        worksheet_index=WorksheetIndex.QUEUE,
        record=record,
        add_uuid=True,
    )
    if result is None:
        return

    await message.answer(f"New record: date: {date}, time: {input_time}, lab: №{lab}")
    await state.clear()

    result = await run_sheet_operation(
        message, sheet_service.sort, worksheet_index=WorksheetIndex.QUEUE
    )
    if result is None:
        return


@router.message(Command("cheat"))
async def add_cheat(
    message: types.Message, dispatcher: Dispatcher, state: FSMContext
) -> None:
    input_name = await input_name_from_db(message, dispatcher)
    if not input_name:
        return

    await state.update_data(input_name=input_name)

    await state.set_state(Cheat.waiting_for_lab)

    keyboard = cancel_keyboard()
    await message.answer("Which lab?", reply_markup=keyboard)


@router.message(Cheat.waiting_for_lab)
async def cheat_input_lab(message: types.Message, state: FSMContext) -> None:
    lab = await parse_lab(message)
    if lab is None:
        return

    await state.update_data(lab=lab)

    if not message.from_user:
        await message.answer("Failed to get user_id")
        return

    await state.set_state(Cheat.waiting_for_cheat)

    keyboard = cancel_keyboard()
    await message.answer("Write a cheat:", reply_markup=keyboard)


@router.message(Cheat.waiting_for_cheat)
async def cheat_input_cheat(message: types.Message, state: FSMContext) -> None:
    input_cheat = message.text
    if not input_cheat:
        await message.answer("Cheat can not be empty. Try again.")
        return

    data = await state.get_data()
    input_name = data.get("input_name")
    lab = data.get("lab")

    record = [input_name, lab, input_cheat]

    result = await run_sheet_operation(
        message,
        sheet_service.add_record,
        worksheet_index=WorksheetIndex.CHEATS,
        record=record,
    )
    if result is None:
        return

    await message.answer("Your cheat was added")
    await state.clear()


@router.message(Command("remove"))
async def remove_record(message: types.Message, dispatcher: Dispatcher) -> None:
    input_name = await input_name_from_db(message, dispatcher)
    if not input_name:
        return

    result = await run_sheet_operation(
        message, sheet_service.sort, WorksheetIndex.QUEUE
    )
    if result is None:
        return

    records = await run_sheet_operation(
        message,
        sheet_service.find_records,
        worksheet_index=WorksheetIndex.QUEUE,
        name=input_name,
    )
    if records is None:
        return
    if not records:
        await message.answer("No records found")
        return

    keyboard = records_keyboard(records, "remove", message.from_user.id)
    await message.answer("Choose the record to remove:", reply_markup=keyboard)


async def show_status_keyboard(
    message: types.Message, action: str, dispatcher: Dispatcher | None = None
):
    # action: "done", "self_done", "missed", "recover"
    result = await run_sheet_operation(
        message, sheet_service.sort, WorksheetIndex.QUEUE
    )
    if result is None:
        return

    if action == "self_done":
        if dispatcher is None:
            logger.error("Dispatcher is required for the done action")
            await message.answer("Unable to load your records.")
            return
        input_name = await input_name_from_db(message, dispatcher)
        if not input_name:
            return
        records = await run_sheet_operation(
            message,
            sheet_service.get_queue_records,
            worksheet_index=WorksheetIndex.QUEUE,
            was=QueueStatus.ACTIVE.value,
            input_name=input_name,
        )
        callback_action = action
        status_text = QueueStatus.DONE.value
    elif action == "done":
        records = await run_sheet_operation(
            message,
            sheet_service.get_queue_records,
            worksheet_index=WorksheetIndex.QUEUE,
            was=QueueStatus.ACTIVE.value,
        )
        callback_action = action
        status_text = action
    elif action == "missed":
        records = await run_sheet_operation(
            message,
            sheet_service.get_queue_records,
            worksheet_index=WorksheetIndex.QUEUE,
            was=QueueStatus.ACTIVE.value,
        )
        callback_action = action
        status_text = action
    elif action == "recover":
        records = await run_sheet_operation(
            message,
            sheet_service.get_queue_records,
            worksheet_index=WorksheetIndex.QUEUE,
            was_not=QueueStatus.ACTIVE.value,
        )
        callback_action = action
        status_text = QueueStatus.ACTIVE.value
    else:
        return

    if records is None:
        return
    if not records:
        await message.answer("No records found")
        return

    keyboard = records_keyboard(records, callback_action, message.from_user.id)
    await message.answer(
        f"Choose the record to make {status_text}:", reply_markup=keyboard
    )


@router.message(Command("done"))
async def cmd_done(message: types.Message, dispatcher: Dispatcher) -> None:
    await show_status_keyboard(message, "done", dispatcher)


@router.message(Command("self_done"))
async def cmd_self_done(message: types.Message, dispatcher: Dispatcher) -> None:
    await show_status_keyboard(message, "self_done", dispatcher)


@router.message(Command("missed"))
async def cmd_missed(message: types.Message) -> None:
    await show_status_keyboard(message, "missed")


@router.message(Command("recover"))
async def cmd_recover(message: types.Message) -> None:
    """
    Return a completed or missed record to the active queue.
    Empty rows without a real name/lab are ignored.
    """
    await show_status_keyboard(message, "recover")


@router.message(Command("again"))
async def cmd_again(message: types.Message, dispatcher: Dispatcher) -> None:
    input_name = await input_name_from_db(message, dispatcher)
    if not input_name:
        return

    result = await run_sheet_operation(
        message, sheet_service.sort, WorksheetIndex.QUEUE
    )
    if result is None:
        return

    records = await run_sheet_operation(
        message,
        sheet_service.get_queue_records,
        worksheet_index=WorksheetIndex.QUEUE,
        was=QueueStatus.DONE.value,
        input_name=input_name,
    )
    if records is None:
        return
    if not records:
        await message.answer(
            "You do not have any completed records to return to the queue."
        )
        return

    keyboard = records_keyboard(records, QueueStatus.ACTIVE.value, message.from_user.id)
    await message.answer(
        "Choose a completed record to move it back to the active queue:",
        reply_markup=keyboard,
    )


@router.message(Command("sheet"))
async def cmd_sheet(message: types.Message) -> None:
    text = f'<a href="{sheet_service.SHEET_URL}">google_sheet</a>'
    await message.answer(
        text,
        parse_mode="HTML",
        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
    )


@router.message(Command("rebirth"))
async def cmd_rebirth(message: types.Message, dispatcher: Dispatcher) -> None:
    """
    return your self record status in "Was?" to "no"
    """

    input_name = await input_name_from_db(message, dispatcher)
    if not input_name:
        return

    result = await run_sheet_operation(
        message, sheet_service.sort, WorksheetIndex.QUEUE
    )
    if result is None:
        return

    records = await run_sheet_operation(
        message,
        sheet_service.get_queue_records,
        worksheet_index=WorksheetIndex.QUEUE,
        was_not=QueueStatus.ACTIVE.value,
        input_name=input_name,
    )
    if records is None:
        return
    if not records:
        await message.answer(
            "You do not have any records that can be reset to active status."
        )
        return

    keyboard = records_keyboard(records, QueueStatus.ACTIVE.value, message.from_user.id)
    await message.answer(
        "Choose a record to reset it back to active status:",
        reply_markup=keyboard,
    )
