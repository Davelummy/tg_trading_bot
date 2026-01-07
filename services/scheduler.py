from __future__ import annotations

import asyncio
import time


_TIMEFRAME_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
}


def timeframe_seconds(tf: str) -> int:
    if tf not in _TIMEFRAME_SECONDS:
        raise ValueError(f"Unsupported timeframe: {tf}")
    return _TIMEFRAME_SECONDS[tf]


async def wait_next_tick(tf: str) -> None:
    seconds = timeframe_seconds(tf)
    now = int(time.time())
    next_tick = ((now // seconds) + 1) * seconds
    await asyncio.sleep(max(0, next_tick - now))
