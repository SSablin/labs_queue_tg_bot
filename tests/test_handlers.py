import pytest
from types import SimpleNamespace

from handlers.start import cmd_start, input_name


class DummyMessage:
    def __init__(self, text=None, from_user=None):
        self.text = text
        self.from_user = from_user
        self.answers = []

    async def answer(self, text, reply_markup=None, parse_mode=None, **kwargs):
        # capture the last answer for assertions
        self.answers.append({"text": text, "reply_markup": reply_markup})


class DummyState:
    def __init__(self):
        self._state = None
        self._data = {}

    async def set_state(self, st):
        self._state = st

    async def update_data(self, **kwargs):
        self._data.update(kwargs)

    async def get_data(self):
        return self._data

    async def clear(self):
        self._data = {}


@pytest.mark.asyncio
async def test_cmd_start_existing_user(monkeypatch):
    # Make input_name_from_db return a name
    async def fake_input_name_from_db(msg, dispatcher):
        return "Alice"

    # Patch the symbol used by handlers.start (it imports input_name_from_db at module import)
    monkeypatch.setattr("handlers.start.input_name_from_db", fake_input_name_from_db)

    msg = DummyMessage(from_user=SimpleNamespace(id=10))
    state = DummyState()
    dispatcher = {}

    await cmd_start(msg, state, dispatcher)

    assert msg.answers, "Expected a reply"
    last = msg.answers[-1]
    assert "Hello, Alice" in last["text"]


@pytest.mark.asyncio
async def test_input_name_creates_user_and_replies(monkeypatch):
    # Replace upsert_user so it doesn't touch DB and just confirms it's called
    async def fake_upsert_user(pool, user_id, username, full_name, input_name):
        # simple assert that values are forwarded
        assert user_id == 42
        assert input_name == "MyName"

    # Patch the upsert_user symbol used by the handler (imported into handlers.start module)
    monkeypatch.setattr("handlers.start.upsert_user", fake_upsert_user)

    msg = DummyMessage(text="MyName", from_user=SimpleNamespace(id=42, username="u", full_name="F"))

    class Disp(dict):
        pass

    dispatcher = Disp(pool=object())
    state = DummyState()

    # call the handler (Start.waiting_for_auth is used as decorator param; direct call is fine)
    await input_name(msg, state, dispatcher)

    assert msg.answers, "Expected a reply after saving name"
    assert any("Your name in table is" in a["text"] or "Name updated successfully" in a["text"] for a in msg.answers)
