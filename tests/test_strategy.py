from engine.models import Candle
from services.config_service import RuntimeConfig
from strategies.ma_atr import MovingAverageAtrStrategy


def test_ma_atr_signal_generation():
    config = RuntimeConfig(
        mode="paper",
        adapter="paper",
        symbols=["BTCUSDT"],
        timeframe="1m",
        fast_ma=3,
        slow_ma=5,
        atr_period=3,
        atr_multiplier=2.0,
        risk_per_trade_pct=1.0,
        max_daily_loss_pct=2.0,
        max_trades_per_day=3,
        max_open_positions=1,
        max_spread=0.01,
        symbol_map={},
    )
    candles = []
    prices = [10, 10, 10, 10, 10, 9, 20]
    for i, p in enumerate(prices):
        candles.append(Candle(ts=1000 + i * 60, open=p, high=p + 0.5, low=p - 0.5, close=p, volume=1))
    strategy = MovingAverageAtrStrategy()
    signal = strategy.generate(candles, config)
    assert signal is not None
    assert signal.side == "BUY"
