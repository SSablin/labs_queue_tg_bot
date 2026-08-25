import gspread
from google.oauth2.service_account import Credentials

from config import CREDITS_PATH, SHEET_URL
from constants.enums import QueueColumn

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
SERVICE_ACCOUNT_FILE = CREDITS_PATH

# TODO: Refactor to casses


creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
client = gspread.authorize(creds)
spreadsheet = client.open_by_url(SHEET_URL)


def get_queue(worksheet_index: int, was: str | None = None) -> list[list[str]]:
    worksheet = spreadsheet.get_worksheet(worksheet_index)
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
    worksheet = spreadsheet.get_worksheet(worksheet_index)
    data = worksheet.get_all_records()
    rows = []

    for i, row in enumerate(data):
        if (
            (was is None or was == row["Was?"])
            and (was_not is None or was_not != row["Was?"])
            and (input_name is None or input_name == row["Name"])
        ):
            rows.append(
                [str(i + 1), str(row["Name"]), str(row["Lab"]), str(row["Was?"])]
            )

    return rows


def add_record(worksheet_index: int, record: list[int | str]) -> None:
    worksheet = spreadsheet.get_worksheet(worksheet_index)
    worksheet.append_row(record, value_input_option="USER_ENTERED")


def find_records(
    worksheet_index: int, name: str, lab: int | None = None
) -> list[list[str]]:
    worksheet = spreadsheet.get_worksheet(worksheet_index)
    data = worksheet.get_all_records()

    rows = []

    for i, row in enumerate(data):
        if row["Name"] == name:
            if lab is None or row["Lab"] == str(lab):
                rows.append(
                    [str(i + 1), str(row["Name"]), str(row["Lab"]), str(row["Was?"])]
                )

    return rows


def update_record(
    worksheet_index: int, row_number: int, values: list[list[int | str]]
) -> None:
    worksheet = spreadsheet.get_worksheet(worksheet_index)
    worksheet.update(values=values, range_name=f"A{row_number}")


def update_cell(
    worksheet_index: int, row_number: int, col_number: int, value: int | str
) -> None:
    worksheet = spreadsheet.get_worksheet(worksheet_index)
    worksheet.update_cell(row=row_number + 1, col=col_number, value=value)


def delete_record(worksheet_index: int, row_index: int) -> None:
    worksheet = spreadsheet.get_worksheet(worksheet_index)
    worksheet.delete_rows(row_index + 1)


def add_tip(worksheet_index: int, name: str, lab: int, tip: str) -> None:
    worksheet = spreadsheet.get_worksheet(worksheet_index)
    worksheet.append_row([name, lab, tip])


def sort(worksheet_index: int) -> None:
    worksheet = spreadsheet.get_worksheet(worksheet_index)
    row_count = worksheet.row_count
    worksheet.sort(
        (QueueColumn.WAS, "des"),
        (QueueColumn.DATE, "asc"),
        (QueueColumn.TIME, "asc"),
        range=f"A2:F{max(row_count, 2)}",
    )
