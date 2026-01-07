from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from loguru import logger

from bot.middleware import AdminOnlyMiddleware, ThrottleMiddleware
from bot.routers import build_router
from data.store import create_store
from services.config_service import BotSettings, ConfigService
from services.notifier import Notifier
from services.orchestrator import EngineOrchestrator


async def main() -> None:
    settings = BotSettings()
    store = create_store(settings.DATABASE_URL or None, settings.DATABASE_PATH)
    config_service = ConfigService(store, settings)
    notifier = Notifier()

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.message.middleware(AdminOnlyMiddleware(settings))
    dp.callback_query.middleware(AdminOnlyMiddleware(settings))
    dp.message.middleware(ThrottleMiddleware())
    dp.callback_query.middleware(ThrottleMiddleware())

    orchestrator = EngineOrchestrator(store, settings, notifier)
    router = build_router(orchestrator, store, config_service)
    dp.include_router(router)

    await notifier.start(bot)
    logger.info("Bot starting")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
