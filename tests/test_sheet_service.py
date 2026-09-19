from constants.enums import QueueColumn, WorksheetIndex
from services.sheet_service import SheetService


class FakeWorksheet:
    row_count = 10

    def __init__(self, rows):
        self.rows = rows
        self.appended = []
        self.updated = []

    def get_all_records(self):
        return self.rows

    def append_row(self, row, value_input_option):
        self.appended.append((row, value_input_option))

    def update(self, values, range_name):
        self.updated.append((values, range_name))

    def update_cell(self, row, column, value):
        self.updated.append((row, column, value))

    def sort(self, *args, **kwargs):
        self.sort_args = (args, kwargs)


class FakeSpreadsheet:
    def __init__(self, worksheet):
        self.worksheet = worksheet

    def get_worksheet(self, index):
        assert index == WorksheetIndex.QUEUE
        return self.worksheet


def test_add_queue_record_appends_uuid_without_mutating_input():
    worksheet = FakeWorksheet([])
    service = SheetService(FakeSpreadsheet(worksheet))
    record = ["Alice", "19.09.2026", "22:00", 17, "no"]

    service.add_record(
        WorksheetIndex.QUEUE,
        record,
        add_uuid=True,
    )

    appended, option = worksheet.appended[0]
    assert appended[:5] == record
    assert len(appended[5]) == 36
    assert option == "USER_ENTERED"
    assert record == ["Alice", "19.09.2026", "22:00", 17, "no"]


def test_complete_record_updates_entire_row_in_one_operation():
    worksheet = FakeWorksheet(
        [
            {
                "Name": "Alice",
                "Date": "18.09.2026",
                "Time": "12:00",
                "Lab": "17",
                "Was?": "no",
                "record_id": "record-1",
            }
        ]
    )
    service = SheetService(FakeSpreadsheet(worksheet))

    result = service.complete_record_by_id(
        WorksheetIndex.QUEUE,
        "record-1",
        "19.09.2026",
        "22:00",
    )

    assert result == "updated"
    assert worksheet.updated == [
        (
            [["Alice", "19.09.2026", "22:00", "17", "done", "record-1"]],
            "A2:F2",
        )
    ]


def test_complete_record_does_not_overwrite_inactive_record():
    worksheet = FakeWorksheet(
        [{"record_id": "record-1", "Was?": "done"}]
    )
    service = SheetService(FakeSpreadsheet(worksheet))

    result = service.complete_record_by_id(
        WorksheetIndex.QUEUE,
        "record-1",
        "19.09.2026",
        "22:00",
    )

    assert result == "inactive"
    assert worksheet.updated == []
