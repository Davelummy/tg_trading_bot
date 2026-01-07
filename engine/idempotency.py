from __future__ import annotations

from typing import Iterable

from data.store import SQLiteStore


class Idempotency:
    def __init__(self, store: SQLiteStore, max_keys: int = 100) -> None:
        self.store = store
        self.max_keys = max_keys

    def _load(self) -> list[str]:
        keys = self.store.get_setting("IDEMPOTENCY_KEYS", [])
        if not isinstance(keys, list):
            return []
        return keys

    def _save(self, keys: list[str]) -> None:
        self.store.set_setting("IDEMPOTENCY_KEYS", keys)

    def exists(self, key: str) -> bool:
        return key in self._load()

    def add(self, key: str) -> None:
        keys = self._load()
        if key in keys:
            return
        keys.append(key)
        keys = keys[-self.max_keys :]
        self._save(keys)

    def check_and_add(self, key: str) -> bool:
        if self.exists(key):
            return False
        self.add(key)
        return True
