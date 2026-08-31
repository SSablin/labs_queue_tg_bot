import asyncio
import logging

logger = logging.getLogger(__name__)


async def run_sheet_operation(message, func, *args, **kwargs):
    try:
        result = await asyncio.to_thread(func, *args, **kwargs)
        return True if result is None else result
    except Exception:
        logger.exception("Sheet error while running %s", getattr(func, '__name__', str(func)))
        await message.answer("Error accessing Google Sheet.")
        return None
