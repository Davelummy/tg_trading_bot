from __future__ import annotations

import time
from dataclasses import dataclass

from data.store import BaseStore
from engine.models import OrderIntent, Signal
from services.config_service import RuntimeConfig


@dataclass
class RiskDecision:
    allowed: bool
    reason: str | None
    qty: float | None
    circuit_breaker: bool = False


class RiskManager:
    def __init__(self, store: BaseStore) -> None:
        self.store = store
        self._last_notify_ts: dict[str, int] = {}

    def evaluate(
        self,
        user_id: int,
        symbol: str,
        signal: Signal,
        last_price: float,
        open_positions: int,
        config: RuntimeConfig,
        spread: float,
    ) -> RiskDecision:
        if spread > config.max_spread:
            return RiskDecision(False, f"Spread too high: {spread:.6f}", None)
        if open_positions >= config.max_open_positions:
            return RiskDecision(False, "Max open positions reached", None)

        day_start = int(time.time()) - (int(time.time()) % 86400)
        trades_today = self.store.list_trades_since(user_id, day_start)
        if len(trades_today) >= config.max_trades_per_day:
            return RiskDecision(False, "Max trades per day reached", None)

        pnl_pct = self.store.compute_daily_pnl_pct(user_id, day_start)
        if pnl_pct <= -abs(config.max_daily_loss_pct):
            return RiskDecision(
                False,
                f"Circuit breaker: daily PnL {pnl_pct:.2f}%",
                None,
                circuit_breaker=True,
            )

        stop_distance = abs(last_price - signal.stop_loss)
        if stop_distance <= 0:
            return RiskDecision(False, "Invalid stop distance", None)

        risk_amount = last_price * (config.risk_per_trade_pct / 100.0)
        qty = risk_amount / stop_distance
        if qty <= 0:
            return RiskDecision(False, "Invalid position size", None)

        return RiskDecision(True, None, qty)
