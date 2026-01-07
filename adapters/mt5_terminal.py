from __future__ import annotations

import asyncio
import time
from typing import Any

try:
    import MetaTrader5 as mt5
except Exception:  # pragma: no cover - runtime gated
    mt5 = None

from adapters.base import BrokerAdapter
from engine.models import Candle, Fill, OrderIntent, Position


class MT5Adapter(BrokerAdapter):
    def __init__(self, login: str, password: str, server: str, symbol_map: dict[str, str] | None = None) -> None:
        self.login = login
        self.password = password
        self.server = server
        self.symbol_map = symbol_map or {}
        self._initialized = False

    def _ensure_init(self) -> None:
        if not mt5:
            raise RuntimeError("MetaTrader5 package not installed")
        if self._initialized:
            return
        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        if not mt5.login(int(self.login), password=self.password, server=self.server):
            raise RuntimeError(f"MT5 login failed: {mt5.last_error()}")
        self._initialized = True

    def _map_symbol(self, symbol: str) -> str:
        return self.symbol_map.get(symbol, symbol)

    async def fetch_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[Candle]:
        self._ensure_init()
        tf_map = {"1m": mt5.TIMEFRAME_M1, "5m": mt5.TIMEFRAME_M5, "15m": mt5.TIMEFRAME_M15, "1h": mt5.TIMEFRAME_H1}
        tf = tf_map.get(timeframe)
        if tf is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        mapped = self._map_symbol(symbol)
        rates = await asyncio.to_thread(mt5.copy_rates_from_pos, mapped, tf, 0, limit)
        if rates is None:
            raise RuntimeError(f"MT5 copy_rates failed: {mt5.last_error()}")
        candles = [
            Candle(ts=int(r[0]), open=float(r[1]), high=float(r[2]), low=float(r[3]), close=float(r[4]), volume=float(r[5]))
            for r in rates
        ]
        return candles

    async def get_positions(self) -> list[Position]:
        self._ensure_init()
        positions = await asyncio.to_thread(mt5.positions_get)
        if positions is None:
            return []
        results = []
        for p in positions:
            results.append(Position(symbol=p.symbol, qty=float(p.volume), avg_price=float(p.price_open)))
        return results

    async def get_spread(self, symbol: str) -> float:
        self._ensure_init()
        mapped = self._map_symbol(symbol)
        tick = await asyncio.to_thread(mt5.symbol_info_tick, mapped)
        if tick is None:
            raise RuntimeError(f"MT5 tick failed: {mt5.last_error()}")
        if tick.ask == 0:
            return 0.0
        return (tick.ask - tick.bid) / tick.ask

    async def place_order(self, intent: OrderIntent) -> Fill:
        self._ensure_init()
        mapped = self._map_symbol(intent.symbol)
        symbol_info = mt5.symbol_info(mapped)
        if symbol_info is None:
            raise RuntimeError(f"MT5 symbol info failed: {mt5.last_error()}")
        if not symbol_info.visible:
            mt5.symbol_select(mapped, True)
        order_type = mt5.ORDER_TYPE_BUY if intent.side == "BUY" else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(mapped).ask if intent.side == "BUY" else mt5.symbol_info_tick(mapped).bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": mapped,
            "volume": intent.qty,
            "type": order_type,
            "price": price,
            "deviation": 10,
            "magic": 234000,
            "comment": "tg-bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = await asyncio.to_thread(mt5.order_send, request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            raise RuntimeError(f"MT5 order failed: {result}")
        return Fill(order_id=str(result.order), symbol=intent.symbol, side=intent.side, qty=intent.qty, price=price)
