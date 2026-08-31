import pytest

import asyncio

from utils.sheet import run_sheet_operation


class DummyMessage:
    def __init__(self):
        self.answers = []

    async def answer(self, text):
        self.answers.append(text)


@pytest.mark.asyncio
async def test_run_sheet_operation_returns_value():
    msg = DummyMessage()

    def func(a, b):
        return a + b

    res = await run_sheet_operation(msg, func, 2, 3)
    assert res == 5
    assert not msg.answers


@pytest.mark.asyncio
async def test_run_sheet_operation_returns_true_for_none():
    msg = DummyMessage()

    def func():
        return None

    res = await run_sheet_operation(msg, func)
    assert res is True
    assert not msg.answers


@pytest.mark.asyncio
async def test_run_sheet_operation_handles_exception():
    msg = DummyMessage()

    def func():
        raise ValueError("boom")

    res = await run_sheet_operation(msg, func)
    assert res is None
    assert msg.answers
    assert "Error accessing Google Sheet." in msg.answers[-1]
