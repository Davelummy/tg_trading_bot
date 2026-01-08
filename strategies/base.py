from __future__ import annotations

from abc import ABC, abstractmethod

from engine.models import Candle, Signal
from services.config_service import RuntimeConfig


class Strategy(ABC):
    @abstractmethod
    def generate(self, candles: list[Candle], config: RuntimeConfig) -> Signal | None:
        raise NotImplementedError
