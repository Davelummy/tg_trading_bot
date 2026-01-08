from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from engine.models import Candle, Fill, OrderIntent, Position


class BrokerAdapter(ABC):
    @abstractmethod
    async def fetch_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[Candle]:
        raise NotImplementedError

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        raise NotImplementedError

    @abstractmethod
    async def get_spread(self, symbol: str) -> float:
        raise NotImplementedError

    @abstractmethod
    async def place_order(self, intent: OrderIntent) -> Fill:
        raise NotImplementedError
