import time

from data.store import SQLiteStore
from engine.models import Signal
from risk.manager import RiskManager
from services.config_service import RuntimeConfig


def _config() -> RuntimeConfig:
    return RuntimeConfig(
        mode="paper",
        adapter="paper",
        symbols=["BTCUSDT"],
        timeframe="1m",
        fast_ma=5,
        slow_ma=10,
        atr_period=14,
        atr_multiplier=2.0,
        risk_per_trade_pct=1.0,
        max_daily_loss_pct=2.0,
        max_trades_per_day=1,
        max_open_positions=1,
        max_spread=0.0001,
        symbol_map={},
    )


def test_risk_spread_block(tmp_path):
    store = SQLiteStore(str(tmp_path / "r.db"))
    rm = RiskManager(store)
    signal = Signal(side="BUY", reason="test", stop_loss=99.0)
    decision = rm.evaluate(1, "BTCUSDT", signal, last_price=100.0, open_positions=0, config=_config(), spread=0.01)
    assert not decision.allowed


def test_risk_max_trades(tmp_path):
    store = SQLiteStore(str(tmp_path / "r2.db"))
    store.add_trade(1, "BTCUSDT", "BUY", 1.0, 100.0, "paper", "paper", None)
    rm = RiskManager(store)
    signal = Signal(side="BUY", reason="test", stop_loss=99.0)
    decision = rm.evaluate(1, "BTCUSDT", signal, last_price=100.0, open_positions=0, config=_config(), spread=0.0)
    assert not decision.allowed


def test_risk_circuit_breaker(tmp_path):
    store = SQLiteStore(str(tmp_path / "r3.db"))
    store.add_trade(1, "BTCUSDT", "BUY", 1.0, 100.0, "paper", "paper", None)
    store.add_trade(1, "BTCUSDT", "SELL", 1.0, 90.0, "paper", "paper", None)
    rm = RiskManager(store)
    cfg = _config()
    cfg.max_trades_per_day = 5
    signal = Signal(side="BUY", reason="test", stop_loss=99.0)
    decision = rm.evaluate(1, "BTCUSDT", signal, last_price=100.0, open_positions=0, config=cfg, spread=0.0)
    assert decision.circuit_breaker
