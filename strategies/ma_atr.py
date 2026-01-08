from __future__ import annotations

import pandas as pd

from engine.models import Candle, Signal
from services.config_service import RuntimeConfig
from strategies.base import Strategy


class MovingAverageAtrStrategy(Strategy):
    def generate(self, candles: list[Candle], config: RuntimeConfig) -> Signal | None:
        if len(candles) < max(config.fast_ma, config.slow_ma, config.atr_period) + 2:
            return None
        df = pd.DataFrame([c.__dict__ for c in candles])
        df["fast"] = df["close"].rolling(config.fast_ma).mean()
        df["slow"] = df["close"].rolling(config.slow_ma).mean()
        df["tr"] = pd.concat(
            [
                df["high"] - df["low"],
                (df["high"] - df["close"].shift()).abs(),
                (df["low"] - df["close"].shift()).abs(),
            ],
            axis=1,
        ).max(axis=1)
        df["atr"] = df["tr"].rolling(config.atr_period).mean()

        prev = df.iloc[-2]
        last = df.iloc[-1]
        if pd.isna(prev["fast"]) or pd.isna(prev["slow"]) or pd.isna(last["atr"]):
            return None

        if prev["fast"] <= prev["slow"] and last["fast"] > last["slow"]:
            stop_loss = last["close"] - (last["atr"] * config.atr_multiplier)
            return Signal(side="BUY", reason="MA cross up", stop_loss=float(stop_loss))
        if prev["fast"] >= prev["slow"] and last["fast"] < last["slow"]:
            stop_loss = last["close"] + (last["atr"] * config.atr_multiplier)
            return Signal(side="SELL", reason="MA cross down", stop_loss=float(stop_loss))
        return None
