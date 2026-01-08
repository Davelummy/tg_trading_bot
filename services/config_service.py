from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from data.store import BaseStore


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    TELEGRAM_BOT_TOKEN: str = ""
    ADMIN_TELEGRAM_IDS: str = ""
    MODE: str = "paper"
    ADAPTER: str = "paper"
    SYMBOLS: str = "BTCUSDT"
    TIMEFRAME: str = "15m"
    FAST_MA: int = 20
    SLOW_MA: int = 50
    ATR_PERIOD: int = 14
    ATR_MULTIPLIER: float = 2.0
    RISK_PER_TRADE_PCT: float = 1.0
    MAX_DAILY_LOSS_PCT: float = 2.0
    MAX_TRADES_PER_DAY: int = 3
    MAX_OPEN_POSITIONS: int = 1
    MAX_SPREAD: float = 0.0002
    BINANCE_API_KEY: str = ""
    BINANCE_API_SECRET: str = ""
    MT5_LOGIN: str = ""
    MT5_PASSWORD: str = ""
    MT5_SERVER: str = ""
    SYMBOL_MAP: str = "{}"
    TELEGRAM_CHAT_ID: str = ""
    DATABASE_PATH: str = "./bot.db"
    DATABASE_URL: str = ""
    CREDENTIAL_ENCRYPTION_KEY: str = ""
    ALLOW_ALL_USERS: bool = True


class RuntimeConfig(BaseModel):
    mode: str
    adapter: str
    symbols: list[str]
    timeframe: str
    fast_ma: int
    slow_ma: int
    atr_period: int
    atr_multiplier: float
    risk_per_trade_pct: float
    max_daily_loss_pct: float
    max_trades_per_day: int
    max_open_positions: int
    max_spread: float
    symbol_map: dict[str, str]


class ConfigService:
    def __init__(self, store: BaseStore, base: BotSettings) -> None:
        self.store = store
        self.base = base

    def load(self, user_id: int) -> RuntimeConfig:
        def _get(key: str, default: Any) -> Any:
            return self.store.get_setting(user_id, key, default)

        symbol_map_raw = _get("SYMBOL_MAP", self.base.SYMBOL_MAP)
        try:
            symbol_map = json.loads(symbol_map_raw) if isinstance(symbol_map_raw, str) else symbol_map_raw
        except json.JSONDecodeError:
            symbol_map = {}
        return RuntimeConfig(
            mode=_get("MODE", self.base.MODE),
            adapter=_get("ADAPTER", self.base.ADAPTER),
            symbols=_get("SYMBOLS", self.base.SYMBOLS).split(","),
            timeframe=_get("TIMEFRAME", self.base.TIMEFRAME),
            fast_ma=int(_get("FAST_MA", self.base.FAST_MA)),
            slow_ma=int(_get("SLOW_MA", self.base.SLOW_MA)),
            atr_period=int(_get("ATR_PERIOD", self.base.ATR_PERIOD)),
            atr_multiplier=float(_get("ATR_MULTIPLIER", self.base.ATR_MULTIPLIER)),
            risk_per_trade_pct=float(_get("RISK_PER_TRADE_PCT", self.base.RISK_PER_TRADE_PCT)),
            max_daily_loss_pct=float(_get("MAX_DAILY_LOSS_PCT", self.base.MAX_DAILY_LOSS_PCT)),
            max_trades_per_day=int(_get("MAX_TRADES_PER_DAY", self.base.MAX_TRADES_PER_DAY)),
            max_open_positions=int(_get("MAX_OPEN_POSITIONS", self.base.MAX_OPEN_POSITIONS)),
            max_spread=float(_get("MAX_SPREAD", self.base.MAX_SPREAD)),
            symbol_map=symbol_map,
        )

    def update(self, key: str, value: Any) -> None:
        raise ValueError("Use update_for_user")

    def update_for_user(self, user_id: int, key: str, value: Any) -> None:
        self.store.set_setting(user_id, key, value)
