import asyncio
import logging

from aiogram import Dispatcher, types

from database.session_manager import get_user
from utils.str import parse_str_date

logger = logging.getLogger(__name__)


async def input_name_from_db(
    user_id: int,
    message: types.Message,
    dispatcher: Dispatcher,
) -> str | None:
    pool = dispatcher.get("pool")
    if not pool:
        logger.error("DB error: dispatcher has no 'pool' configured")
        await message.answer("Error: no connection to DB")
        return None
    try:
        return await get_user(pool, user_id)
    except Exception:
        logger.exception("DB error while fetching user %s", user_id)
        await message.answer("Connection error")
        return None


async def parse_lab(message: types.Message) -> int | None:
    input_lab = message.text
    if not input_lab:
        await message.answer("Lab can not be empty. Try again.")
        return None

    try:
        lab = int(input_lab)
    except ValueError:
        await message.answer("Lab must be integer. Try again.")
        return None

    if lab <= 0:
        await message.answer("Lab must be a positive integer. Try again.")
        return None

    return lab


async def parse_date(message: types.Message) -> dict[str, str] | None:
    input_text = message.text
    if not input_text:
        await message.answer("Data can not be empty. Try again.")
        return None
    date = await asyncio.to_thread(parse_str_date, input_text)
    if not date:
        await message.answer("Invalid date format. Try again.")
        return None

    return date
