from types import SimpleNamespace

import pytest

from constants.enums import QueueColumn, QueueStatus, WorksheetIndex
from handlers.sheet import show_status_keyboard
from keyboards.inline import (
    action_callback,
    own_queue_keyboard,
    quick_record_action_callback,
)


class DummyMessage:
    def __init__(self, from_user=None):
        self.from_user = from_user
        self.answers = []
        self.edited_reply_markup = []
        self.edited_text = []

    async def answer(self, text, **kwargs):
        self.answers.append((text, kwargs))

    async def edit_reply_markup(self, **kwargs):
        self.edited_reply_markup.append(kwargs)

    async def edit_text(self, text, **kwargs):
        self.edited_text.append((text, kwargs))


class DummyCallback:
    def __init__(self, data, user_id=42, message=None):
        self.data = data
        self.from_user = SimpleNamespace(id=user_id)
        self.message = message or DummyMessage(self.from_user)
        self.answers = []
        self.edited_reply_markup = []

    async def answer(self, text=None, **kwargs):
        self.answers.append((text, kwargs))


@pytest.mark.asyncio
async def test_own_queue_keyboard_has_time_and_done_buttons():
    keyboard = own_queue_keyboard(
        [["3", "Alice", "17", QueueStatus.ACTIVE.value, "record-1"]],
        user_id=42,
    )

    assert len(keyboard.inline_keyboard) == 1
    buttons = keyboard.inline_keyboard[0]
    assert buttons[0].text.endswith("— сейчас")
    assert buttons[0].callback_data == "quick_time:record-1:42"
    assert buttons[1].text == "done"
    assert buttons[1].callback_data == "quick_done:record-1:42"


@pytest.mark.asyncio
async def test_quick_done_updates_owner_record_status_and_time(monkeypatch):
    message = DummyMessage(SimpleNamespace(id=42))
    callback = DummyCallback("quick_done:record-1:42", message=message)
    dispatcher = {}
    updates = []

    async def fake_input_name_from_db(message, dispatcher):
        return "Alice"

    def fake_get_record_by_id(worksheet_index, record_id):
        assert worksheet_index == WorksheetIndex.QUEUE
        assert record_id == "record-1"
        return {"Name": "Alice"}

    def fake_update_cell_by_id(worksheet_index, record_id, column, value):
        updates.append((worksheet_index, record_id, column, value))
        return True

    monkeypatch.setattr(
        "keyboards.inline.input_name_from_db", fake_input_name_from_db
    )
    monkeypatch.setattr(
        "keyboards.inline.get_current_sheet_datetime",
        lambda: ("19.09.2026", "21:47"),
    )
    monkeypatch.setattr(
        "keyboards.inline.sheet_service.get_record_by_id",
        fake_get_record_by_id,
    )
    monkeypatch.setattr(
        "keyboards.inline.sheet_service.update_cell_by_id",
        fake_update_cell_by_id,
    )

    await quick_record_action_callback(callback, dispatcher)

    assert updates == [
        (WorksheetIndex.QUEUE, "record-1", QueueColumn.WAS, QueueStatus.DONE.value),
        (WorksheetIndex.QUEUE, "record-1", QueueColumn.DATE, "19.09.2026"),
        (WorksheetIndex.QUEUE, "record-1", QueueColumn.TIME, "21:47"),
    ]
    assert callback.answers[-1][0] == "Updated"
    assert message.edited_reply_markup == [{"reply_markup": None}]


@pytest.mark.asyncio
async def test_quick_time_does_not_update_foreign_record(monkeypatch):
    message = DummyMessage(SimpleNamespace(id=42))
    callback = DummyCallback("quick_time:record-1:42", message=message)
    updates = []

    async def fake_input_name_from_db(message, dispatcher):
        return "Alice"

    monkeypatch.setattr(
        "keyboards.inline.input_name_from_db", fake_input_name_from_db
    )
    monkeypatch.setattr(
        "keyboards.inline.sheet_service.get_record_by_id",
        lambda worksheet_index, record_id: {"Name": "Bob"},
    )
    monkeypatch.setattr(
        "keyboards.inline.sheet_service.update_cell_by_id",
        lambda *args: updates.append(args),
    )

    await quick_record_action_callback(callback, {})

    assert updates == []
    assert callback.answers[-1] == (
        "This is not your record.",
        {"show_alert": True},
    )


@pytest.mark.asyncio
async def test_done_command_loads_all_active_records(monkeypatch):
    message = DummyMessage(SimpleNamespace(id=42))
    calls = []

    async def fake_run_sheet_operation(message, func, *args, **kwargs):
        calls.append((func, args, kwargs))
        if func.__name__ == "sort":
            return True
        return [["1", "Alice", "17", QueueStatus.ACTIVE.value, "record-1"]]

    monkeypatch.setattr("handlers.sheet.run_sheet_operation", fake_run_sheet_operation)

    await show_status_keyboard(message, "done", {})

    get_records_call = next(call for call in calls if call[0].__name__ == "get_queue_records")
    assert get_records_call[2]["was"] == QueueStatus.ACTIVE.value
    assert "input_name" not in get_records_call[2]
    assert "Choose the record to make done:" == message.answers[-1][0]


@pytest.mark.asyncio
async def test_self_done_command_loads_only_current_user_records(monkeypatch):
    message = DummyMessage(SimpleNamespace(id=42))
    calls = []

    async def fake_input_name_from_db(message, dispatcher):
        return "Alice"

    async def fake_run_sheet_operation(message, func, *args, **kwargs):
        calls.append((func, args, kwargs))
        if func.__name__ == "sort":
            return True
        return [["1", "Alice", "17", QueueStatus.ACTIVE.value, "record-1"]]

    monkeypatch.setattr("handlers.sheet.input_name_from_db", fake_input_name_from_db)
    monkeypatch.setattr("handlers.sheet.run_sheet_operation", fake_run_sheet_operation)

    await show_status_keyboard(message, "self_done", {})

    get_records_call = next(call for call in calls if call[0].__name__ == "get_queue_records")
    assert get_records_call[2]["was"] == QueueStatus.ACTIVE.value
    assert get_records_call[2]["input_name"] == "Alice"
    assert message.answers[-1][0] == "Choose the record to make done:"


@pytest.mark.asyncio
async def test_done_callback_can_update_foreign_record(monkeypatch):
    message = DummyMessage(SimpleNamespace(id=42))
    callback = DummyCallback("done:record-1:42", message=message)
    updates = []

    monkeypatch.setattr(
        "keyboards.inline.sheet_service.update_cell_by_id",
        lambda worksheet, record_id, column, value: updates.append(
            (worksheet, record_id, column, value)
        )
        or True,
    )
    monkeypatch.setattr(
        "keyboards.inline.get_current_sheet_datetime",
        lambda: ("19.09.2026", "21:51"),
    )

    await action_callback(callback, {})

    assert updates[0] == (
        WorksheetIndex.QUEUE,
        "record-1",
        QueueColumn.WAS,
        QueueStatus.DONE.value,
    )
    assert message.edited_text[-1][0] == "Status was updated to <b>done</b>."


@pytest.mark.asyncio
async def test_self_done_callback_rejects_foreign_record(monkeypatch):
    message = DummyMessage(SimpleNamespace(id=42))
    callback = DummyCallback("self_done:record-1:42", message=message)

    async def fake_input_name_from_db(message, dispatcher):
        return "Alice"

    monkeypatch.setattr(
        "keyboards.inline.input_name_from_db", fake_input_name_from_db
    )
    monkeypatch.setattr(
        "keyboards.inline.sheet_service.get_record_by_id",
        lambda worksheet, record_id: {"Name": "Bob"},
    )

    await action_callback(callback, {})

    assert callback.answers[-1] == (
        "This is not your record.",
        {"show_alert": True},
    )
