import asyncio
import logging

import asyncpg
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DB_CONFIG, PROXY
from database import init_db
from handlers.sheet import router as sheet_router
from handlers.start import router as start_router
from keyboards.inline import router as inline_router


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN is not set")

    session = AiohttpSession(proxy=PROXY)

    bot = Bot(
        token=BOT_TOKEN,
        session=session,
        default=DefaultBotProperties(parse_mode=None),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start_router)
    dp.include_router(sheet_router)
    dp.include_router(inline_router)

    try:
        pool = await asyncpg.create_pool(
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            host=DB_CONFIG["host"],
            port=DB_CONFIG.get("port", 5432),
            min_size=5,
            max_size=20,
        )
    except Exception:
        logger.critical("Failed to connect to DB", exc_info=True)
        return

    try:
        await init_db(pool)
    except Exception:
        logger.exception("Error with initializing db")

    logger.info("Pool connections with DB was successfully created")

    dp["pool"] = pool

    async def on_shutdown():
        await pool.close()
        logger.info("Pool connections was closed")

    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
