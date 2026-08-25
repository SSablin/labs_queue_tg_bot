import logging

from aiogram import Dispatcher, types

from database.session_manager import get_user

logger = logging.getLogger(__name__)


async def input_name_from_db(
    message: types.Message, dispatcher: Dispatcher
) -> str | None:
    pool = dispatcher["pool"]
    if pool is None:
        logger.error("DB error")
        await message.answer("Error: no connection with DB")
        return None

    if not message.from_user:
        await message.answer("Failed to get user_id")
        return

    try:
        input_name = await get_user(
            pool,
            message.from_user.id,
        )
    except Exception as e:
        logger.error(f"DB error: {e}")
        await message.answer("Connection error")
        return

    return input_name


async def parse_lab(message: types.Message) -> int | None:
    input_lab = message.text
    if not input_lab:
        await message.answer("Lab can not be empty. Try again.")
        return

    try:
        lab = int(input_lab)
    except ValueError:
        await message.answer("Lab must be integer. Try again.")
        return

    if lab <= 0:
        await message.answer("Lab must be a positive integer. Try again.")
        return None

    return lab
