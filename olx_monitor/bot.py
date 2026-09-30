"""Entry point: aiogram 3 bot + background asyncio monitoring task."""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from .config import load_config
from .database import init_db
from .handlers import router
from .monitor import monitor_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("olx_monitor")


async def main() -> None:
    config = load_config()
    await init_db(config.db_path)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp["config"] = config  # injected into handlers as `config`
    dp.include_router(router)

    # Background task: check all subscriptions every N seconds.
    checker = asyncio.create_task(monitor_loop(bot, config))
    log.info("Bot starting (polling), check interval=%ds", config.check_interval_sec)
    try:
        await dp.start_polling(bot)
    finally:
        checker.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
