from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class Candle:
    ts: int
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Signal:
    side: Literal["BUY", "SELL"]
    reason: str
    stop_loss: float


@dataclass
class OrderIntent:
    symbol: str
    side: Literal["BUY", "SELL"]
    qty: float
    price: float | None
    stop_loss: float


@dataclass
class Order:
    id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    qty: float
    price: float


@dataclass
class Fill:
    order_id: str
    symbol: str
    side: Literal["BUY", "SELL"]
    qty: float
    price: float


@dataclass
class Position:
    symbol: str
    qty: float
    avg_price: float


@dataclass
class TradeRecord:
    symbol: str
    side: Literal["BUY", "SELL"]
    qty: float
    price: float
    mode: str
    adapter: str
    order_id: str | None
