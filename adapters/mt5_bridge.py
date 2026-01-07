from __future__ import annotations

import httpx

from adapters.base import BrokerAdapter
from engine.models import Candle, Fill, OrderIntent, Position


class MT5BridgeAdapter(BrokerAdapter):
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    async def fetch_candles(self, symbol: str, timeframe: str, limit: int = 200) -> list[Candle]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/candles", params={"symbol": symbol, "tf": timeframe, "limit": limit})
            resp.raise_for_status()
            data = resp.json()
        return [Candle(**row) for row in data]

    async def get_positions(self) -> list[Position]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/positions")
            resp.raise_for_status()
            data = resp.json()
        return [Position(**row) for row in data]

    async def get_spread(self, symbol: str) -> float:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.base_url}/spread", params={"symbol": symbol})
            resp.raise_for_status()
            data = resp.json()
        return float(data["spread"])

    async def place_order(self, intent: OrderIntent) -> Fill:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f"{self.base_url}/order", json=intent.__dict__)
            resp.raise_for_status()
            data = resp.json()
        return Fill(**data)
