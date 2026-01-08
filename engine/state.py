from __future__ import annotations

import time
from dataclasses import dataclass

from data.store import BaseStore


@dataclass
class EngineState:
    last_candle_ts: int | None
    last_error: str | None
    kill_switch: bool
    paused: bool


class EngineStateStore:
    def __init__(self, store: BaseStore, user_id: int) -> None:
        self.store = store
        self.user_id = user_id

    def load(self) -> EngineState:
        row = self.store.get_engine_state(self.user_id)
        return EngineState(
            last_candle_ts=row.get("last_candle_ts"),
            last_error=row.get("last_error"),
            kill_switch=bool(row.get("kill_switch")),
            paused=bool(row.get("paused")),
        )

    def update(self, **kwargs) -> None:
        kwargs["updated_at"] = int(time.time())
        self.store.set_engine_state(self.user_id, **kwargs)
