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
        return

    if not message.from_user:
        await message.answer("Failed to get user_id")
        return

    try:
        input_name = await get_user(
            pool,
            message.from_user.id,
        )
    except Exception as e:
        logger.error(f"UPSERT error: {e}")
        await message.answer("Connection error")
        return

    if not input_name:
        logger.error(f"No input_name in db for user_id: {message.from_user.id}")
        await message.answer("No name in database. Did you authorize?")
        return

    return input_name
