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

from constants.enums import WorksheetIndex
from keyboards.inline import cancel_keyboard, records_keyboard
from services import sheet_service
from states.sheet import Add, Cheat
from utils.input import input_name_from_db, parse_lab
from utils.sheet import run_sheet_operation

router = Router()

logger = logging.getLogger(__name__)


@router.message(Command("queue"))
async def cmd_queue(message: types.Message) -> None:
    result = await run_sheet_operation(
        message, sheet_service.sort, worksheet_index=WorksheetIndex.QUEUE
    )
    if result is None:
        return

    data = await run_sheet_operation(
        message, sheet_service.get_queue, WorksheetIndex.QUEUE, "no"
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
    await message.answer_rich(rich_message=rich_message)


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

    record = [input_name, date, input_time, lab, "no"]

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


async def show_status_keyboard(message, action):
    # action: "done", "missed", "recover"
    result = await run_sheet_operation(
        message, sheet_service.sort, WorksheetIndex.QUEUE
    )
    if result is None:
        return

    if action in ("done", "missed"):
        records = await run_sheet_operation(
            message,
            sheet_service.get_queue_records,
            worksheet_index=WorksheetIndex.QUEUE,
            was="no",
        )
        status_text = action
    elif action == "recover":
        records = await run_sheet_operation(
            message,
            sheet_service.get_queue_records,
            worksheet_index=WorksheetIndex.QUEUE,
            was_not="no",
        )
        status_text = "no"
    else:
        return

    if records is None:
        return
    if not records:
        await message.answer("No records found")
        return

    keyboard = records_keyboard(records, status_text, message.from_user.id)
    await message.answer(
        f"Choose the record to make {status_text}:", reply_markup=keyboard
    )


@router.message(Command("done"))
async def cmd_done(message: types.Message) -> None:
    await show_status_keyboard(message, "done")


@router.message(Command("missed"))
async def cmd_missed(message: types.Message) -> None:
    await show_status_keyboard(message, "missed")


@router.message(Command("recover"))
async def cmd_recover(message: types.Message) -> None:
    """
    return record status in "Was?" to "no"
    """
    await show_status_keyboard(message, "recover")


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
        was_not="no",
        input_name=input_name,
    )
    if records is None:
        return
    if not records:
        await message.answer("No records found")
        return

    keyboard = records_keyboard(records, "no", message.from_user.id)
    await message.answer("Choose the record to make no:", reply_markup=keyboard)
