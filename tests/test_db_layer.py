import pytest
from types import SimpleNamespace

import asyncio

from database.session_manager import get_user
from database.db import upsert_user


class _FakeConn:
    def __init__(self):
        self.fetchval_called = False
        self.fetchval_args = None
        self.execute_called = False
        self.execute_args = None

    async def fetchval(self, sql, *args):
        self.fetchval_called = True
        self.fetchval_args = (sql, args)
        # return a fake input_name
        return "TestUser"

    async def execute(self, sql, *args):
        self.execute_called = True
        self.execute_args = (sql, args)
        return "OK"


class _FakeAcquire:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        return _FakeAcquire(self.conn)


@pytest.mark.asyncio
async def test_get_user_returns_value():
    conn = _FakeConn()
    pool = _FakePool(conn)

    res = await get_user(pool, 123)
    assert res == "TestUser"
    assert conn.fetchval_called
    sql, args = conn.fetchval_args
    assert "SELECT input_name" in sql
    assert args[0] == 123


@pytest.mark.asyncio
async def test_upsert_user_executes_sql():
    conn = _FakeConn()
    pool = _FakePool(conn)

    await upsert_user(pool, 7, "userX", "Full Name", "inputX")

    assert conn.execute_called
    sql, args = conn.execute_args
    # basic assertions about executed SQL and parameters
    assert "INSERT INTO users" in sql
    assert args[0] == 7
    assert args[1] == "userX"
    assert args[2] == "Full Name"
    assert args[3] == "inputX"
