from __future__ import annotations

import random
import time
from typing import Optional

from loguru import logger

from adapters.base import BrokerAdapter
from engine.models import Candle, Fill, OrderIntent, Position


class PaperAdapter(BrokerAdapter):
    def __init__(self, data_provider: BrokerAdapter, slippage_bps: float = 2.0, fee_bps: float = 1.0) -> None:
        self.data_provider = data_provider
        self.slippage_bps = slippage_bps
        self.fee_bps = fee_bps
        self._positions: dict[str, Position] = {}

    async def fetch_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[Candle]:
        return await self.data_provider.fetch_candles(symbol, timeframe, limit=limit)

    async def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    async def get_spread(self, symbol: str) -> float:
        return await self.data_provider.get_spread(symbol)

    async def place_order(self, intent: OrderIntent) -> Fill:
        candles = await self.fetch_candles(intent.symbol, "1m", limit=1)
        if not candles:
            raise RuntimeError("No candles available for fill")
        price = candles[-1].close
        slip = price * (self.slippage_bps / 10000.0) * random.uniform(0.5, 1.5)
        fill_price = price + slip if intent.side == "BUY" else price - slip
        fee = fill_price * (self.fee_bps / 10000.0)
        final_price = fill_price + fee if intent.side == "BUY" else fill_price - fee
        fill = Fill(
            order_id=f"paper-{int(time.time() * 1000)}",
            symbol=intent.symbol,
            side=intent.side,
            qty=intent.qty,
            price=final_price,
        )
        self._apply_fill(fill)
        logger.info("Paper fill: {}", fill)
        return fill

    def _apply_fill(self, fill: Fill) -> None:
        pos = self._positions.get(fill.symbol)
        if not pos:
            qty = fill.qty if fill.side == "BUY" else -fill.qty
            self._positions[fill.symbol] = Position(fill.symbol, qty, fill.price)
            return
        new_qty = pos.qty + (fill.qty if fill.side == "BUY" else -fill.qty)
        if new_qty == 0:
            self._positions.pop(fill.symbol, None)
            return
        avg_price = ((pos.avg_price * pos.qty) + (fill.price * fill.qty)) / new_qty
        self._positions[fill.symbol] = Position(fill.symbol, new_qty, avg_price)
