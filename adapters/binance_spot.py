from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Any

from binance.client import Client
from binance.exceptions import BinanceAPIException
from loguru import logger

from adapters.base import BrokerAdapter
from engine.models import Candle, Fill, OrderIntent, Position


_TIMEFRAME_MAP = {
    "1m": Client.KLINE_INTERVAL_1MINUTE,
    "5m": Client.KLINE_INTERVAL_5MINUTE,
    "15m": Client.KLINE_INTERVAL_15MINUTE,
    "1h": Client.KLINE_INTERVAL_1HOUR,
}


class BinanceSpotAdapter(BrokerAdapter):
    def __init__(self, api_key: str = "", api_secret: str = "") -> None:
        self.client = Client(api_key, api_secret)
        self._precision_cache: dict[str, dict[str, Decimal]] = {}
        self._has_keys = bool(api_key and api_secret)

    async def fetch_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[Candle]:
        interval = _TIMEFRAME_MAP.get(timeframe)
        if not interval:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        klines = await asyncio.to_thread(self.client.get_klines, symbol=symbol, interval=interval, limit=limit)
        candles = []
        for k in klines:
            candles.append(
                Candle(
                    ts=int(k[0] / 1000),
                    open=float(k[1]),
                    high=float(k[2]),
                    low=float(k[3]),
                    close=float(k[4]),
                    volume=float(k[5]),
                )
            )
        return candles

    async def get_positions(self) -> list[Position]:
        return []

    async def get_spread(self, symbol: str) -> float:
        depth = await asyncio.to_thread(self.client.get_order_book, symbol=symbol, limit=5)
        bid = float(depth["bids"][0][0])
        ask = float(depth["asks"][0][0])
        return (ask - bid) / ask

    async def place_order(self, intent: OrderIntent) -> Fill:
        if not self._has_keys:
            raise RuntimeError("Binance API keys missing for live order")
        qty = self._round_qty(intent.symbol, intent.qty)
        side = Client.SIDE_BUY if intent.side == "BUY" else Client.SIDE_SELL
        try:
            resp = await asyncio.to_thread(
                self.client.create_order,
                symbol=intent.symbol,
                side=side,
                type=Client.ORDER_TYPE_MARKET,
                quantity=str(qty),
            )
        except BinanceAPIException as exc:
            raise RuntimeError(f"Binance order failed: {exc.message}") from exc
        fills = resp.get("fills", [])
        price = float(fills[0]["price"]) if fills else float(resp.get("price", 0.0))
        order_id = str(resp.get("orderId"))
        return Fill(order_id=order_id, symbol=intent.symbol, side=intent.side, qty=float(qty), price=price)

    def _round_qty(self, symbol: str, qty: float) -> float:
        info = self._precision_cache.get(symbol)
        if not info:
            info = self._load_precision(symbol)
            self._precision_cache[symbol] = info
        step = info["step"]
        rounded = (Decimal(str(qty)) // step) * step
        return float(rounded)

    def _load_precision(self, symbol: str) -> dict[str, Decimal]:
        info = self.client.get_symbol_info(symbol)
        if not info:
            raise RuntimeError(f"Symbol not found: {symbol}")
        lot_filter = next(f for f in info["filters"] if f["filterType"] == "LOT_SIZE")
        step = Decimal(lot_filter["stepSize"])
        return {"step": step}
