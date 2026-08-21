import logging

from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


async def clear_fsm_logic(state: FSMContext) -> bool:
    current_state = await state.get_state()
    if current_state is None:
        return False

    logger.info("Cancelling state %r", current_state)
    await state.clear()
    return True
