from __future__ import annotations

import asyncio

from aiogram import Bot, Dispatcher
from loguru import logger

from bot.middleware import AdminOnlyMiddleware, ThrottleMiddleware
from bot.routers import build_router
from data.store import SQLiteStore
from engine.state import EngineStateStore
from services.config_service import BotSettings, ConfigService
from services.notifier import Notifier
from services.orchestrator import EngineOrchestrator


async def main() -> None:
    settings = BotSettings()
    store = SQLiteStore(settings.DATABASE_PATH)
    config_service = ConfigService(store, settings)
    state_store = EngineStateStore(store)
    notifier = Notifier()

    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    dp.message.middleware(AdminOnlyMiddleware(settings))
    dp.callback_query.middleware(AdminOnlyMiddleware(settings))
    dp.message.middleware(ThrottleMiddleware())
    dp.callback_query.middleware(ThrottleMiddleware())

    orchestrator = EngineOrchestrator(store, settings, notifier)
    router = build_router(orchestrator, store, config_service, state_store)
    dp.include_router(router)

    await notifier.start(bot)
    logger.info("Bot starting")
    chat_id = settings.TELEGRAM_CHAT_ID or (settings.ADMIN_TELEGRAM_IDS.split(",")[0].strip() if settings.ADMIN_TELEGRAM_IDS else "")
    if chat_id:
        await notifier.send(chat_id, "Bot startup")
    try:
        await dp.start_polling(bot)
    finally:
        if chat_id:
            await notifier.send(chat_id, "Bot shutdown")


if __name__ == "__main__":
    asyncio.run(main())
