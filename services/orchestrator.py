from __future__ import annotations

import asyncio

from loguru import logger

from adapters.binance_spot import BinanceSpotAdapter
from adapters.mt5_terminal import MT5Adapter
from adapters.paper import PaperAdapter
from data.store import SQLiteStore
from engine.core import TradingEngine
from engine.state import EngineStateStore
from services.config_service import BotSettings, ConfigService
from services.notifier import Notifier
from strategies.ma_atr import MovingAverageAtrStrategy


class EngineOrchestrator:
    def __init__(self, store: SQLiteStore, settings: BotSettings, notifier: Notifier) -> None:
        self.store = store
        self.settings = settings
        self.notifier = notifier
        self.config_service = ConfigService(store, settings)
        self.state_store = EngineStateStore(store)
        self._task: asyncio.Task | None = None
        self._engine: TradingEngine | None = None

    def _build_adapter(self):
        config = self.config_service.load()
        if config.adapter == "binance":
            return BinanceSpotAdapter(self.settings.BINANCE_API_KEY, self.settings.BINANCE_API_SECRET)
        if config.adapter == "mt5":
            return MT5Adapter(self.settings.MT5_LOGIN, self.settings.MT5_PASSWORD, self.settings.MT5_SERVER, config.symbol_map)
        if config.adapter == "paper":
            data_provider = BinanceSpotAdapter(self.settings.BINANCE_API_KEY, self.settings.BINANCE_API_SECRET)
            return PaperAdapter(data_provider)
        raise ValueError(f"Unknown adapter: {config.adapter}")

    async def start(self, chat_id: str | None = None) -> None:
        if self._task and not self._task.done():
            return
        self.state_store.update(paused=0)
        adapter = self._build_adapter()
        self._engine = TradingEngine(adapter, self.store, self.config_service, self.notifier, MovingAverageAtrStrategy())
        self._task = asyncio.create_task(self._engine.run_forever(chat_id=chat_id))
        logger.info("Engine started")

    async def pause(self) -> None:
        self.state_store.update(paused=1)
        logger.info("Engine paused")

    async def stop(self) -> None:
        if self._engine:
            self._engine.stop()
        if self._task:
            await asyncio.sleep(0)
        self.state_store.update(paused=1)
        logger.info("Engine stopped")

    async def kill(self) -> None:
        self.state_store.update(kill_switch=1, paused=1)
        logger.warning("Kill switch engaged")

    async def resume(self) -> None:
        self.state_store.update(kill_switch=0, paused=0)
        await self.start()
