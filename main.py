import asyncio
import logging
import sys

import asyncpg
import gspread
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from google.oauth2.service_account import Credentials

from config import Config, load_config
from database import init_db
from handlers.sheet import router as sheet_router
from handlers.start import router as start_router
from keyboards.inline import router as inline_router
from services import sheet_service


async def _init_db_pool(cfg: Config, logger) -> asyncpg.Pool:
    try:
        pool = await asyncpg.create_pool(
            user=cfg.db_user,
            password=cfg.db_password,
            database=cfg.db_name,
            host=cfg.db_host,
            port=cfg.db_port,
            min_size=5,
            max_size=20,
        )
    except Exception:
        logger.critical("Failed to connect to DB", exc_info=True)
        raise

    try:
        await init_db(pool)
    except Exception:
        logger.critical("Failed to init DB schema", exc_info=True)
        await pool.close()
        raise

    logger.info("Pool connections with DB was successfully created")
    return pool


def _init_sheets(cfg: Config, logger) -> None:
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    try:
        creds = Credentials.from_service_account_file(cfg.credits_path, scopes=SCOPES)
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_url(cfg.sheet_url)
        sheet_service.init_service(spreadsheet)
        logger.info("Google Sheets client initialized")
    except Exception:
        logger.critical("Failed to initialize Google Sheets client", exc_info=True)
        raise


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    try:
        cfg = load_config()
    except (RuntimeError, ValueError):
        logger.critical("Invalid configuration", exc_info=True)
        sys.exit(1)

    session = AiohttpSession(proxy=cfg.proxy)
    bot = Bot(
        token=cfg.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=None),
    )

    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start_router)
    dp.include_router(sheet_router)
    dp.include_router(inline_router)

    # Fail-fast
    try:
        pool = await _init_db_pool(cfg, logger)
        _init_sheets(cfg, logger)
    except Exception:
        await bot.session.close()
        sys.exit(1)

    dp["pool"] = pool
    dp["config"] = cfg

    async def on_shutdown():
        await pool.close()
        await bot.session.close()
        logger.info("Pool connections was closed")

    dp.shutdown.register(on_shutdown)

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
