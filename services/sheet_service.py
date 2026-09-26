import logging
import uuid
from typing import Optional

from constants.enums import QueueColumn

logger = logging.getLogger(__name__)


class SheetService:
    """Service wrapper around a gspread.Spreadsheet object.

    This allows injecting the spreadsheet dependency at application startup
    (in main) and makes the service easier to test.
    """

    def __init__(self, spreadsheet):
        self.spreadsheet = spreadsheet

    def get_queue(
        self, worksheet_index: int, was: str | None = None
    ) -> list[list[str]]:
        worksheet = self.spreadsheet.get_worksheet(worksheet_index)
        data = worksheet.get_all_records()
        headers = ["№", "Name", "Date", "Time", "Lab", "Was?"]
        rows = [headers]

        for i, row in enumerate(data):
            if was is None or row.get("Was?") == was:
                rows.append(
                    [
                        str(i + 1),
                        str(row.get("Name", "")),
                        str(row.get("Date", "")),
                        str(row.get("Time", "")),
                        str(row.get("Lab", "")),
                        str(row.get("Was?", "")),
                    ]
                )

        return rows

    def _is_valid_record_row(self, row: dict) -> bool:
        if not row.get("record_id", ""):
            return False

        name = str(row.get("Name", "")).strip()
        lab = str(row.get("Lab", "")).strip()

        if not name and not lab:
            logger.warning("Skipping empty record row without name/lab: %s", row)
            return False
        return True

    def get_queue_records(
        self,
        worksheet_index: int,
        was: str | None = None,
        was_not: str | None = None,
        input_name: str | None = None,
    ) -> list[list[str]]:
        worksheet = self.spreadsheet.get_worksheet(worksheet_index)
        data = worksheet.get_all_records()
        rows = []

        for i, row in enumerate(data):
            if not self._is_valid_record_row(row):
                continue
            if (
                (was is None or was == row.get("Was?"))
                and (was_not is None or was_not != row.get("Was?"))
                and (input_name is None or input_name == row.get("Name"))
            ):
                rows.append(
                    [
                        str(i + 1),
                        str(row.get("Name", "")),
                        str(row.get("Lab", "")),
                        str(row.get("Was?", "")),
                        str(row.get("record_id", "")),
                    ]
                )
        return rows

    def add_record(
        self,
        worksheet_index: int,
        record: list,
        add_uuid: bool = False,
    ) -> None:
        row = list(record)
        if add_uuid:
            row.append(str(uuid.uuid4()))
        worksheet = self.spreadsheet.get_worksheet(worksheet_index)
        worksheet.append_row(row, value_input_option="USER_ENTERED")

    def find_records(
        self, worksheet_index: int, name: str, lab: int | None = None
    ) -> list[list[str]]:
        worksheet = self.spreadsheet.get_worksheet(worksheet_index)
        data = worksheet.get_all_records()

        rows = []
        for i, row in enumerate(data):
            if row.get("Name") == name:
                if row.get("record_id", ""):
                    if lab is None or row.get("Lab") == str(lab):
                        rows.append(
                            [
                                str(i + 1),
                                str(row.get("Name", "")),
                                str(row.get("Lab", "")),
                                str(row.get("Was?", "")),
                                str(row.get("record_id", "")),
                            ]
                        )
                else:
                    logger.warning("No record_id in row: %s", row)
        return rows

    def update_record(
        self,
        worksheet_index: int,
        values: list[list[int | str]],
        row_number: int | None = None,
        record_id: str | None = None,
    ) -> None:
        worksheet = self.spreadsheet.get_worksheet(worksheet_index)
        if not row_number and record_id:
            row_number = self._find_row_number_by_record_id(worksheet, record_id)
        elif not row_number and not record_id:
            return

        worksheet.update(
            values=values,
            range_name=f"A{row_number}",
            value_input_option="USER_ENTERED",
        )

    def add_tip(self, worksheet_index: int, name: str, lab: int, tip: str) -> None:
        worksheet = self.spreadsheet.get_worksheet(worksheet_index)
        worksheet.append_row([name, lab, tip])

    def sort(self, worksheet_index: int) -> None:
        worksheet = self.spreadsheet.get_worksheet(worksheet_index)
        row_count = worksheet.row_count
        worksheet.sort(
            (QueueColumn.WAS, "des"),
            (QueueColumn.DATE, "asc"),
            (QueueColumn.TIME, "asc"),
            range=f"A2:F{max(row_count, 2)}",
        )

    def _find_row_number_by_record_id(self, worksheet, record_id: str) -> Optional[int]:
        data = worksheet.get_all_records()
        for i, row in enumerate(data):
            if str(row.get("record_id")) == record_id:
                return i + 2  # +2 because i is zero-based and first row is header
        return None

    def delete_record_by_id(self, worksheet_index: int, record_id: str) -> bool:
        worksheet = self.spreadsheet.get_worksheet(worksheet_index)
        row_number = self._find_row_number_by_record_id(worksheet, record_id)
        if row_number is None:
            return False
        worksheet.delete_rows(row_number)
        return True

    def update_cell_by_id(
        self, worksheet_index: int, record_id: str, col_number: int, value
    ) -> bool:
        worksheet = self.spreadsheet.get_worksheet(worksheet_index)
        row_number = self._find_row_number_by_record_id(worksheet, record_id)
        if row_number is None:
            return False
        worksheet.update_cell(row_number, col_number, value)
        return True

    def complete_record_by_id(
        self,
        worksheet_index: int,
        record_id: str,
        date: str,
        time: str,
    ) -> str:
        worksheet = self.spreadsheet.get_worksheet(worksheet_index)
        data = worksheet.get_all_records()
        for i, row in enumerate(data):
            if str(row.get("record_id")) != record_id:
                continue
            if row.get("Was?") != "no":
                return "inactive"
            row_number = i + 2
            values = [
                [
                    row.get("Name", ""),
                    date,
                    time,
                    row.get("Lab", ""),
                    "done",
                    row.get("record_id", ""),
                ]
            ]
            worksheet.update(
                values=values,
                range_name=f"A{row_number}:F{row_number}",
                value_input_option="USER_ENTERED",
            )
            return "updated"
        return "not_found"

    def fill_uuid_rows(self, worksheet_index: int) -> None:
        worksheet = self.spreadsheet.get_worksheet(worksheet_index)
        data = worksheet.get_all_records()
        for i, row in enumerate(data):
            if not row.get("record_id"):
                worksheet.update_cell(i + 2, QueueColumn.RECORD_ID, str(uuid.uuid4()))

    def get_record_by_id(self, worksheet_index: int, record_id: str) -> Optional[dict]:
        worksheet = self.spreadsheet.get_worksheet(worksheet_index)
        data = worksheet.get_all_records()
        for record in data:
            if record.get("record_id") == record_id:
                return record
        return None


# Module-level service instance and initializer
_service: Optional[SheetService] = None


SHEET_URL: str | None = None


def init_service(spreadsheet, sheet_url: str | None = None):
    global _service
    global SHEET_URL
    _service = SheetService(spreadsheet)
    SHEET_URL = sheet_url


def _ensure_service():
    if _service is None:
        raise RuntimeError(
            "SheetService is not initialized. Call init_service(spreadsheet) in application startup."
        )


def get_queue(worksheet_index: int, was: str | None = None) -> list[list[str]]:
    _ensure_service()
    return _service.get_queue(worksheet_index, was)


def get_queue_records(
    worksheet_index: int,
    was: str | None = None,
    was_not: str | None = None,
    input_name: str | None = None,
) -> list[list[str]]:
    _ensure_service()
    return _service.get_queue_records(
        worksheet_index, was=was, was_not=was_not, input_name=input_name
    )


def add_record(worksheet_index: int, record: list, add_uuid: bool = False) -> None:
    _ensure_service()
    return _service.add_record(
        worksheet_index,
        record,
        add_uuid=add_uuid,
    )


def find_records(
    worksheet_index: int, name: str, lab: int | None = None
) -> list[list[str]]:
    _ensure_service()
    return _service.find_records(worksheet_index, name, lab)


def update_record(
    worksheet_index: int,
    values: list[list[int | str]],
    row_number: int | None = None,
    record_id: str | None = None,
) -> None:
    _ensure_service()
    return _service.update_record(
        worksheet_index, values, row_number=row_number, record_id=record_id
    )


def add_tip(worksheet_index: int, name: str, lab: int, tip: str) -> None:
    _ensure_service()
    return _service.add_tip(worksheet_index, name, lab, tip)


def sort(worksheet_index: int) -> None:
    _ensure_service()
    return _service.sort(worksheet_index)


def delete_record_by_id(worksheet_index: int, record_id: str) -> bool:
    _ensure_service()
    return _service.delete_record_by_id(worksheet_index, record_id)


def update_cell_by_id(
    worksheet_index: int, record_id: str, col_number: int, value
) -> bool:
    _ensure_service()
    return _service.update_cell_by_id(worksheet_index, record_id, col_number, value)


def complete_record_by_id(
    worksheet_index: int, record_id: str, date: str, time: str
) -> str:
    _ensure_service()
    return _service.complete_record_by_id(worksheet_index, record_id, date, time)


def fill_uuid_rows(worksheet_index: int) -> None:
    _ensure_service()
    return _service.fill_uuid_rows(worksheet_index)


def get_record_by_id(worksheet_index: int, record_id: str) -> Optional[dict]:
    _ensure_service()
    return _service.get_record_by_id(worksheet_index, record_id)
