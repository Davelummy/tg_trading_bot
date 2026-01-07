from __future__ import annotations

from backtest.metrics import BacktestMetrics


def render_report(metrics: BacktestMetrics) -> str:
    return f"Total trades: {metrics.total_trades}" 
