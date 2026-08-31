import pytest

from types import SimpleNamespace

import asyncio

from utils.input import parse_lab, input_name_from_db


class DummyMessage:
    def __init__(self, text=None, from_user=None):
        self.text = text
        self.from_user = from_user
        self.answers = []

    async def answer(self, text):
        # simulate aiogram Message.answer
        self.answers.append(text)


@pytest.mark.asyncio
async def test_parse_lab_valid():
    msg = DummyMessage(text="3")
    res = await parse_lab(msg)
    assert res == 3


@pytest.mark.asyncio
async def test_parse_lab_empty():
    msg = DummyMessage(text="")
    res = await parse_lab(msg)
    assert res is None
    assert msg.answers, "Expected an answer when input empty"
    assert "Lab can not be empty" in msg.answers[-1]


@pytest.mark.asyncio
async def test_parse_lab_non_int():
    msg = DummyMessage(text="abc")
    res = await parse_lab(msg)
    assert res is None
    assert msg.answers
    assert "Lab must be integer" in msg.answers[-1]


@pytest.mark.asyncio
async def test_parse_lab_negative():
    msg = DummyMessage(text="-1")
    res = await parse_lab(msg)
    assert res is None
    assert msg.answers
    assert "positive integer" in msg.answers[-1]


# Tests for input_name_from_db
@pytest.mark.asyncio
async def test_input_name_no_pool():
    dispatcher = {}
    msg = DummyMessage(text="hello", from_user=SimpleNamespace(id=1))

    res = await input_name_from_db(msg, dispatcher)
    assert res is None
    assert msg.answers
    assert "no connection to DB" in msg.answers[-1]


@pytest.mark.asyncio
async def test_input_name_no_from_user():
    dispatcher = {"pool": object()}
    msg = DummyMessage(text="hello", from_user=None)

    res = await input_name_from_db(msg, dispatcher)
    assert res is None
    assert msg.answers
    assert "Failed to get user_id" in msg.answers[-1]


@pytest.mark.asyncio
async def test_input_name_get_user_success(monkeypatch):
    dispatcher = {"pool": object()}
    msg = DummyMessage(text="hello", from_user=SimpleNamespace(id=42))

    async def fake_get_user(pool, user_id):
        assert user_id == 42
        return "Alice"

    monkeypatch.setattr("utils.input.get_user", fake_get_user)

    res = await input_name_from_db(msg, dispatcher)
    assert res == "Alice"
    assert not msg.answers


@pytest.mark.asyncio
async def test_input_name_get_user_exception(monkeypatch):
    dispatcher = {"pool": object()}
    msg = DummyMessage(text="hello", from_user=SimpleNamespace(id=99))

    async def fake_get_user(pool, user_id):
        raise RuntimeError("boom")

    monkeypatch.setattr("utils.input.get_user", fake_get_user)

    res = await input_name_from_db(msg, dispatcher)
    assert res is None
    assert msg.answers
    assert "Connection error" in msg.answers[-1]
