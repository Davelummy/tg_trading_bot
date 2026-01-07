from __future__ import annotations

import asyncio
import time

from loguru import logger

from adapters.base import BrokerAdapter
from data.store import SQLiteStore
from engine.idempotency import Idempotency
from engine.models import OrderIntent
from engine.state import EngineStateStore
from risk.manager import RiskManager
from services.config_service import ConfigService
from services.notifier import Notifier
from services.scheduler import wait_next_tick
from strategies.base import Strategy


class TradingEngine:
    def __init__(
        self,
        adapter: BrokerAdapter,
        store: SQLiteStore,
        config_service: ConfigService,
        notifier: Notifier,
        strategy: Strategy,
    ) -> None:
        self.adapter = adapter
        self.store = store
        self.config_service = config_service
        self.notifier = notifier
        self.strategy = strategy
        self.state_store = EngineStateStore(store)
        self.idempotency = Idempotency(store)
        self.risk = RiskManager(store)
        self._running = False
        self._last_error_notify_ts = 0
        self._last_summary_day = None

    async def run_forever(self, chat_id: str | None = None) -> None:
        self._running = True
        while self._running:
            await self.run_once(chat_id=chat_id)
            config = self.config_service.load()
            await wait_next_tick(config.timeframe)

    def stop(self) -> None:
        self._running = False

    async def run_once(self, chat_id: str | None = None) -> None:
        config = self.config_service.load()
        state = self.state_store.load()
        self._maybe_send_daily_summary(chat_id)
        if state.kill_switch:
            if not state.paused:
                self.state_store.update(paused=1)
            return
        if state.paused:
            return

        try:
            positions = self.store.list_positions()
            open_positions = [p for p in positions if p.get("qty") not in (0, 0.0)]
            for symbol in config.symbols:
                candles = await self.adapter.fetch_candles(symbol, config.timeframe, limit=200)
                if not candles:
                    continue
                last_candle = candles[-1]
                self.state_store.update(last_candle_ts=last_candle.ts)
                signal = self.strategy.generate(candles, config)
                if not signal:
                    continue
                key = f"{symbol}:{last_candle.ts}:{signal.side}"
                if not self.idempotency.check_and_add(key):
                    logger.info("Idempotency hit for {}", key)
                    continue

                spread = await self.adapter.get_spread(symbol)
                decision = self.risk.evaluate(
                    symbol=symbol,
                    signal=signal,
                    last_price=last_candle.close,
                    open_positions=len(open_positions),
                    config=config,
                    spread=spread,
                )
                if not decision.allowed:
                    self.store.add_risk_event(decision.reason or "risk blocked")
                    if decision.circuit_breaker:
                        self.state_store.update(kill_switch=1, paused=1)
                    if chat_id:
                        await self.notifier.send(chat_id, f"Risk blocked: {decision.reason}")
                    continue

                intent = OrderIntent(
                    symbol=symbol,
                    side=signal.side,
                    qty=decision.qty or 0.0,
                    price=None,
                    stop_loss=signal.stop_loss,
                )
                fill = await self.adapter.place_order(intent)
                self.store.add_trade(
                    symbol=fill.symbol,
                    side=fill.side,
                    qty=fill.qty,
                    price=fill.price,
                    mode=config.mode,
                    adapter=config.adapter,
                    order_id=fill.order_id,
                )
                existing = self.store.list_positions()
                pos = next((p for p in existing if p["symbol"] == fill.symbol), None)
                if pos:
                    new_qty = pos["qty"] + (fill.qty if fill.side == "BUY" else -fill.qty)
                    if new_qty == 0:
                        self.store.upsert_position(fill.symbol, 0.0, fill.price)
                    else:
                        avg_price = ((pos["avg_price"] * pos["qty"]) + (fill.price * fill.qty)) / new_qty
                        self.store.upsert_position(fill.symbol, new_qty, avg_price)
                else:
                    qty = fill.qty if fill.side == "BUY" else -fill.qty
                    self.store.upsert_position(fill.symbol, qty, fill.price)

                if chat_id:
                    await self.notifier.send(chat_id, f"Trade executed: {fill.symbol} {fill.side} {fill.qty} @ {fill.price}")
        except Exception as exc:
            logger.exception("Engine error: {}", exc)
            self.state_store.update(last_error=str(exc))
            now = int(time.time())
            if chat_id and now - self._last_error_notify_ts > 60:
                await self.notifier.send(chat_id, f"Engine error: {exc}")
                self._last_error_notify_ts = now

    def _maybe_send_daily_summary(self, chat_id: str | None) -> None:
        if not chat_id:
            return
        day = int(time.time()) // 86400
        if self._last_summary_day is None:
            self._last_summary_day = day
            return
        if day == self._last_summary_day:
            return
        self._last_summary_day = day
        day_start = int(time.time()) - (int(time.time()) % 86400)
        trades = self.store.list_trades_since(day_start)
        asyncio.create_task(self.notifier.send(chat_id, f"Daily summary: {len(trades)} trades"))
