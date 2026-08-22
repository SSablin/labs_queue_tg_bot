import logging

import gspread
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import InputRichBlockTable
from aiogram.types import (
    RichBlockTableCell,
)
from aiogram.types import InputRichMessage, RichTextBold
from google.oauth2.service_account import Credentials

from config import CREDITS_PATH, SHEET_URL

router = Router()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SERVICE_ACCOUNT_FILE = CREDITS_PATH

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

spreadsheet = client.open_by_url(SHEET_URL)


@router.message(Command("queue"))
async def cmd_queue(message: types.Message) -> None:
    worksheet = spreadsheet.get_worksheet(1)
    data = worksheet.get_all_records()

    if not data:
        await message.answer("Queue is empty")
        return

    headers = ["Name", "Data", "Time", "Number", "Was?"]
    header_cells = [
        RichBlockTableCell(text=RichTextBold(text=h), align="center", valign="middle")
        for h in headers
    ]

    table_grid = [header_cells]

    for item in data:
        row_cells = [
            RichBlockTableCell(
                text=str(item.get("Name", "")), align="left", valign="middle"
            ),
            RichBlockTableCell(
                text=str(item.get("Data", "")), align="left", valign="middle"
            ),
            RichBlockTableCell(
                text=str(item.get("Time", "")), align="left", valign="middle"
            ),
            RichBlockTableCell(
                text=str(item.get("Number", "")), align="left", valign="middle"
            ),
            RichBlockTableCell(
                text=str(item.get("Was?", "")), align="left", valign="middle"
            ),
        ]
        table_grid.append(row_cells)

    table_block = InputRichBlockTable(
        cells=table_grid, is_bordered=True, is_striped=True
    )

    rich_message = InputRichMessage(blocks=[table_block])

    await message.answer_rich(rich_message=rich_message)


