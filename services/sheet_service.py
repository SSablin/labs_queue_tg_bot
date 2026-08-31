import uuid
import logging

import gspread
from google.oauth2.service_account import Credentials

from config import CREDITS_PATH, SHEET_URL
from constants.enums import QueueColumn, WorksheetIndex

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SERVICE_ACCOUNT_FILE = CREDITS_PATH

# TODO: Refactor to classes

logger = logging.getLogger(__name__)

# Lazy initialization of gspread spreadsheet to avoid side-effects at import time
_spreadsheet = None

def _init_spreadsheet():
    global _spreadsheet
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    client = gspread.authorize(creds)
    _spreadsheet = client.open_by_url(SHEET_URL)


def _get_spreadsheet():
    global _spreadsheet
    if _spreadsheet is None:
        _init_spreadsheet()
    return _spreadsheet



def get_queue(worksheet_index: int, was: str | None = None) -> list[list[str]]:
    worksheet = _get_spreadsheet().get_worksheet(worksheet_index)
    data = worksheet.get_all_records()
    headers = ["№", "Name", "Date", "Time", "Lab", "Was?"]
    rows = [headers]

    for i, row in enumerate(data):
        if was is None or row["Was?"] == was:
            rows.append(
                [
                    str(i + 1),
                    str(row["Name"]),
                    str(row["Date"]),
                    str(row["Time"]),
                    str(row["Lab"]),
                    str(row["Was?"]),
                ]
            )

    return rows


def get_queue_records(
    worksheet_index: int,
    was: str | None = None,
    was_not: str | None = None,
    input_name: str | None = None,
) -> list[list[str]]:
    worksheet = _get_spreadsheet().get_worksheet(worksheet_index)
    data = worksheet.get_all_records()
    rows = []

    for i, row in enumerate(data):
        if row.get("record_id", ""):
            if (
                (was is None or was == row["Was?"])
                and (was_not is None or was_not != row["Was?"])
                and (input_name is None or input_name == row["Name"])
            ):
                rows.append(
                    [
                        str(i + 1),
                        str(row["Name"]),
                        str(row["Lab"]),
                        str(row["Was?"]),
                        str(row["record_id"]),
                    ]
                )
        else:
            logger.warning(f"No record_id in row: {row}")
    return rows


def add_record(worksheet_index: int, record: list, add_uuid: bool = False) -> None:
    if add_uuid:
        record_id = str(uuid.uuid4())
        record.append(record_id)
    worksheet = _get_spreadsheet().get_worksheet(worksheet_index)
    worksheet.append_row(record, value_input_option="USER_ENTERED")


def find_records(
    worksheet_index: int, name: str, lab: int | None = None
) -> list[list[str]]:
    worksheet = _get_spreadsheet().get_worksheet(worksheet_index)
    data = worksheet.get_all_records()

    rows = []

    for i, row in enumerate(data):
        if row["Name"] == name:
            if row.get("record_id", ""):
                if lab is None or row["Lab"] == str(lab):
                    rows.append(
                        [
                            str(i + 1),
                            str(row["Name"]),
                            str(row["Lab"]),
                            str(row["Was?"]),
                            str(row["record_id"]),
                        ]
                    )
            else:
                logger.warning(f"No record_id in row: {row}")

    return rows


def update_record(
    worksheet_index: int, row_number: int, values: list[list[int | str]]
) -> None:
    worksheet = _get_spreadsheet().get_worksheet(worksheet_index)
    worksheet.update(values=values, range_name=f"A{row_number}")


def add_tip(worksheet_index: int, name: str, lab: int, tip: str) -> None:
    worksheet = _get_spreadsheet().get_worksheet(worksheet_index)
    worksheet.append_row([name, lab, tip])


def sort(worksheet_index: int) -> None:
    worksheet = _get_spreadsheet().get_worksheet(worksheet_index)
    row_count = worksheet.row_count
    worksheet.sort(
        (QueueColumn.WAS, "des"),
        (QueueColumn.DATE, "asc"),
        (QueueColumn.TIME, "asc"),
        range=f"A2:F{max(row_count, 2)}",
    )


def _find_row_number_by_record_id(worksheet, record_id: str) -> int | None:
    data = worksheet.get_all_records()
    for i, row in enumerate(data):
        if str(row.get("record_id")) == record_id:
            return i + 2  # +2, because i - index (first row is header)
    return None


def delete_record_by_id(worksheet_index: int, record_id: str) -> bool:
    worksheet = _get_spreadsheet().get_worksheet(worksheet_index)
    row_number = _find_row_number_by_record_id(worksheet, record_id)
    if row_number is None:
        return False
    worksheet.delete_rows(row_number)
    return True


def update_cell_by_id(
    worksheet_index: int, record_id: str, col_number: int, value
) -> bool:
    worksheet = _get_spreadsheet().get_worksheet(worksheet_index)
    row_number = _find_row_number_by_record_id(worksheet, record_id)
    if row_number is None:
        return False
    worksheet.update_cell(row_number, col_number, value)
    return True


def fill_uuid_rows(worksheet_index: int) -> None:
    worksheet = _get_spreadsheet().get_worksheet(worksheet_index)
    data = worksheet.get_all_records()
    for i, row in enumerate(data):
        if not row.get("record_id"):
            worksheet.update_cell(i + 2, QueueColumn.RECORD_ID, str(uuid.uuid4()))


def get_record_by_id(worksheet_index: int, record_id: str) -> dict | None:
    worksheet = _get_spreadsheet().get_worksheet(worksheet_index)
    data = worksheet.get_all_records()
    for record in data:
        if record.get("record_id") == record_id:
            return record
    return None
