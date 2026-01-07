from __future__ import annotations

from dataclasses import dataclass

from engine.models import TradeRecord


@dataclass
class BacktestMetrics:
    total_trades: int


def compute_metrics(trades: list[TradeRecord]) -> BacktestMetrics:
    return BacktestMetrics(total_trades=len(trades))
