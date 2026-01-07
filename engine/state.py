from __future__ import annotations

import time
from dataclasses import dataclass

from data.store import SQLiteStore


@dataclass
class EngineState:
    last_candle_ts: int | None
    last_error: str | None
    kill_switch: bool
    paused: bool


class EngineStateStore:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store

    def load(self) -> EngineState:
        row = self.store.get_engine_state()
        return EngineState(
            last_candle_ts=row.get("last_candle_ts"),
            last_error=row.get("last_error"),
            kill_switch=bool(row.get("kill_switch")),
            paused=bool(row.get("paused")),
        )

    def update(self, **kwargs) -> None:
        kwargs["updated_at"] = int(time.time())
        self.store.set_engine_state(**kwargs)
