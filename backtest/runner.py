from __future__ import annotations

import pandas as pd

from engine.models import Candle, TradeRecord
from services.config_service import RuntimeConfig
from strategies.ma_atr import MovingAverageAtrStrategy


def run_backtest(csv_path: str, config: RuntimeConfig) -> list[TradeRecord]:
    df = pd.read_csv(csv_path)
    candles = [
        Candle(
            ts=int(row["timestamp"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row.get("volume", 0)),
        )
        for _, row in df.iterrows()
    ]
    strategy = MovingAverageAtrStrategy()
    trades: list[TradeRecord] = []
    for i in range(config.slow_ma + config.atr_period, len(candles)):
        window = candles[: i + 1]
        signal = strategy.generate(window, config)
        if not signal:
            continue
        last = window[-1]
        trades.append(
            TradeRecord(
                symbol=config.symbols[0],
                side=signal.side,
                qty=1.0,
                price=last.close,
                mode="backtest",
                adapter="csv",
                order_id=None,
            )
        )
    return trades
