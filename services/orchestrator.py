from __future__ import annotations

import asyncio

from loguru import logger

import json

from adapters.binance_spot import BinanceSpotAdapter
from adapters.mt5_terminal import MT5Adapter
from adapters.paper import PaperAdapter
from data.store import BaseStore
from engine.core import TradingEngine
from engine.state import EngineStateStore
from services.config_service import BotSettings, ConfigService
from services.crypto import decrypt, build_fernet
from services.notifier import Notifier
from strategies.ma_atr import MovingAverageAtrStrategy


class EngineOrchestrator:
    def __init__(self, store: BaseStore, settings: BotSettings, notifier: Notifier) -> None:
        self.store = store
        self.settings = settings
        self.notifier = notifier
        self.config_service = ConfigService(store, settings)
        self._tasks: dict[int, asyncio.Task] = {}
        self._engines: dict[int, TradingEngine] = {}
        self._fernet = build_fernet(settings.CREDENTIAL_ENCRYPTION_KEY)

    def _load_credentials(self, user_id: int, adapter: str) -> dict:
        blob = self.store.get_credentials(user_id, adapter)
        if not blob:
            return {}
        data = json.loads(decrypt(self._fernet, blob))
        return data

    def _build_adapter(self, user_id: int):
        config = self.config_service.load(user_id)
        if config.adapter == "binance":
            creds = self._load_credentials(user_id, "binance")
            return BinanceSpotAdapter(creds.get("api_key", ""), creds.get("api_secret", ""))
        if config.adapter == "mt5":
            creds = self._load_credentials(user_id, "mt5")
            return MT5Adapter(
                str(creds.get("login", "")),
                str(creds.get("password", "")),
                str(creds.get("server", "")),
                config.symbol_map,
            )
        if config.adapter == "paper":
            data_provider = BinanceSpotAdapter("", "")
            return PaperAdapter(data_provider)
        raise ValueError(f"Unknown adapter: {config.adapter}")

    async def start(self, user_id: int, chat_id: str | None = None) -> None:
        task = self._tasks.get(user_id)
        if task and not task.done():
            return
        state_store = EngineStateStore(self.store, user_id)
        state_store.update(paused=0)
        adapter = self._build_adapter(user_id)
        engine = TradingEngine(adapter, self.store, self.config_service, self.notifier, MovingAverageAtrStrategy(), user_id=user_id)
        self._engines[user_id] = engine
        self._tasks[user_id] = asyncio.create_task(engine.run_forever(chat_id=chat_id))
        logger.info("Engine started for user {}", user_id)

    async def pause(self, user_id: int) -> None:
        state_store = EngineStateStore(self.store, user_id)
        state_store.update(paused=1)
        logger.info("Engine paused for user {}", user_id)

    async def stop(self, user_id: int) -> None:
        engine = self._engines.get(user_id)
        if engine:
            engine.stop()
        task = self._tasks.get(user_id)
        if task:
            await asyncio.sleep(0)
        state_store = EngineStateStore(self.store, user_id)
        state_store.update(paused=1)
        logger.info("Engine stopped for user {}", user_id)

    async def kill(self, user_id: int) -> None:
        state_store = EngineStateStore(self.store, user_id)
        state_store.update(kill_switch=1, paused=1)
        logger.warning("Kill switch engaged for user {}", user_id)

    async def resume(self, user_id: int, chat_id: str | None = None) -> None:
        state_store = EngineStateStore(self.store, user_id)
        state_store.update(kill_switch=0, paused=0)
        await self.start(user_id, chat_id=chat_id)
