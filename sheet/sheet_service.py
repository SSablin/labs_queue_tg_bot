import logging
import gspread

from prettytable import PrettyTable
from google.oauth2.service_account import Credentials
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from config import CREDITS_PATH, SHEET_URL

router = Router()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 
          'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = CREDITS_PATH

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)

spreadsheet = client.open_by_url(SHEET_URL)

@router.message(Command("queue"))
async def cmd_add(message: types.Message) -> None:
    worksheet = spreadsheet.get_worksheet(1)

    data = worksheet.get_all_records()

    table = PrettyTable()
    table.field_names = ["Name", "Data", "Time", "Number", "Was?"]

    for item in data:
        table.add_row([item["Name"], item["Data"], item["Time"], item["Number"], item["Was?"]])

    response = f"<pre>{table.get_string()}</pre>"
    
    await message.answer(response, parse_mode=ParseMode.HTML)


