import asyncio
import logging
import re

from aiogram import Dispatcher, F, Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InputRichBlockTable,
    InputRichMessage,
    RichBlockTableCell,
    RichTextBold,
)

from keyboards.inline import cancel_keyboard, records_keyboard
from services import sheet_service
from states.sheet import Add, Cheat
from utils.fsm import clear_fsm_logic
from utils.input import input_name_from_db

router = Router()

logger = logging.getLogger(__name__)


@router.message(Command("queue"))
async def cmd_queue(message: types.Message) -> None:
    try:
        await asyncio.to_thread(sheet_service.sort, 0)
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    try:
        data = await asyncio.to_thread(sheet_service.get_queue, 0)
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    if not data:
        await message.answer("Queue is empty")
        return

    table_grid = []

    for i, item in enumerate(data):
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

    keyboard = await cancel_keyboard()
    await message.answer("Which lab?", reply_markup=keyboard)


@router.message(Add.waiting_for_lab)
async def input_lab(message: types.Message, state: FSMContext) -> None:
    input_lab = message.text
    if not input_lab:
        await message.answer("Lab can not be empty. Try again.")
        return
    try:
        lab = int(input_lab)
    except Exception:
        await message.answer("Lab must be integer. Try again.")
        return

    await state.update_data(lab=lab)

    if not message.from_user:
        await message.answer("Failed to get user_id")
        return

    await state.set_state(Add.waiting_for_date)

    keyboard = await cancel_keyboard()
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

    keyboard = await cancel_keyboard()
    await message.answer("Which time?", reply_markup=keyboard)


@router.message(Add.waiting_for_time)
async def input_time(message: types.Message, state: FSMContext) -> None:
    input_time = message.text
    if not input_time:
        await message.answer("Time can not be empty. Try again")
        return

    pattern = r"^(0?\d|1\d|2[0-3]):[0-5]?\d(:[0-5]\d)?$"
    if not re.fullmatch(pattern, input_time):
        await message.answer("Time is incorrect. Send time in format: [H]H:[M]M[:SS]")
        return

    data = await state.get_data()
    input_name = data.get("input_name")
    lab = data.get("lab")
    date = data.get("date")

    record = [input_name, date, input_time, lab, "no"]

    try:
        await asyncio.to_thread(sheet_service.add_record, 0, record)
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    await message.answer(f"New record: date: {date}, time: {input_time}, lab: №{lab}")
    await state.clear()

    try:
        await asyncio.to_thread(sheet_service.sort, 0)
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
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

    keyboard = await cancel_keyboard()
    await message.answer("Which lab?", reply_markup=keyboard)


@router.message(Cheat.waiting_for_lab)
async def cheat_input_lab(message: types.Message, state: FSMContext) -> None:
    # TODO: remove this function, make input_lab() universal
    input_lab = message.text
    if not input_lab:
        await message.answer("Lab can not be empty. Try again.")
        return
    try:
        lab = int(input_lab)
    except Exception:
        await message.answer("Lab must be integer. Try again.")
        return

    await state.update_data(lab=lab)

    if not message.from_user:
        await message.answer("Failed to get user_id")
        return

    await state.set_state(Cheat.waiting_for_cheat)

    keyboard = await cancel_keyboard()
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

    try:
        await asyncio.to_thread(sheet_service.add_record, 2, record)
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    await message.answer("Your cheat was added")
    await state.clear()


@router.message(Command("remove"))
async def remove_record(message: types.Message, dispatcher: Dispatcher) -> None:
    input_name = await input_name_from_db(message, dispatcher)
    if not input_name:
        return

    try:
        await asyncio.to_thread(sheet_service.sort, 0)
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    try:
        records = await asyncio.to_thread(sheet_service.find_records, 0, input_name)
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    if not records:
        await message.answer("No records found")
        return

    keyboard = await records_keyboard(records, "remove")
    await message.answer("Choose the record to remove:", reply_markup=keyboard)


@router.message(Command("done"))
async def cmd_done(message: types.Message) -> None:
    # TODO: add input by message (1 2 3 make done the rows: 1, 2, 3)
    try:
        await asyncio.to_thread(sheet_service.sort, 0)
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    try:
        records = await asyncio.to_thread(sheet_service.get_queue_records, 0, "done")
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    keyboard = await records_keyboard(records, "done")
    await message.answer("Choose the record to make done:", reply_markup=keyboard)


@router.message(Command("missed"))
async def cmd_missed(message: types.Message) -> None:
    try:
        await asyncio.to_thread(sheet_service.sort, 0)
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    try:
        records = await asyncio.to_thread(sheet_service.get_queue_records, 0, "missed")
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    keyboard = await records_keyboard(records, "missed")
    await message.answer("Choose the record to make missed:", reply_markup=keyboard)


@router.message(Command("sheet"))
async def cmd_sheet(message: types.Message) -> None:
    text = f'<a href="{sheet_service.SHEET_URL}">google_sheet</a>'

    await message.answer(text, parse_mode="HTML", link_preview_options=None)


@router.message(Command("recover"))
async def cmd_recover(message: types.Message) -> None:
    """
    return record status in "Was?" to "no"
    """
    try:
        await asyncio.to_thread(sheet_service.sort, 0)
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    try:
        records = await asyncio.to_thread(sheet_service.get_queue_records, 0, "no")
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    keyboard = await records_keyboard(records, "no")
    await message.answer("Choose the record to make no:", reply_markup=keyboard)


@router.message(Command("rebirth"))
async def cmd_rebirth(message: types.Message, dispatcher: Dispatcher) -> None:
    """
    return your self record status in "Was?" to "no"
    """
    input_name = await input_name_from_db(message, dispatcher)
    if not input_name:
        return

    try:
        await asyncio.to_thread(sheet_service.sort, 0)
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    try:
        records = await asyncio.to_thread(
            sheet_service.get_queue_records, 0, "no", input_name
        )
    except Exception as e:
        logger.error(f"Sheet error: {e}")
        await message.answer("Error writing to the table.")
        return

    keyboard = await records_keyboard(records, "no")
    await message.answer("Choose the record to make no:", reply_markup=keyboard)
