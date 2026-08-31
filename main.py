import asyncio
import logging

import asyncpg
import gspread
from google.oauth2.service_account import Credentials
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, DB_CONFIG, PROXY, CREDITS_PATH, SHEET_URL
from database import init_db
from handlers.sheet import router as sheet_router
from handlers.start import router as start_router
from keyboards.inline import router as inline_router
from services import sheet_service


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

    # Initialize DB connection pool
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

    # Initialize Google Sheets client and inject into sheet_service
    try:
        SCOPES = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_file(CREDITS_PATH, scopes=SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(SHEET_URL)
        sheet_service.init_service(spreadsheet)
        logger.info("Google Sheets client initialized")
    except Exception:
        logger.exception("Failed to initialize Google Sheets client. Sheet operations will fail at runtime.")

    async def on_shutdown():
        await pool.close()
        logger.info("Pool connections was closed")

    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
