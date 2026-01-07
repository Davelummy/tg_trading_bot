from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable


class SQLiteStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        with self._connect() as conn:
            conn.executescript(schema_path.read_text())
            conn.execute(
                "INSERT OR IGNORE INTO engine_state (id, updated_at) VALUES (1, ?)",
                (int(time.time()),),
            )

    def set_setting(self, key: str, value: Any) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, json.dumps(value)),
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
            if not row:
                return default
            return json.loads(row["value"])

    def set_engine_state(self, **kwargs: Any) -> None:
        keys = ",".join(kwargs.keys())
        placeholders = ",".join(["?"] * len(kwargs))
        values = list(kwargs.values())
        with self._connect() as conn:
            conn.execute(
                f"UPDATE engine_state SET {', '.join([f'{k}=?' for k in kwargs.keys()])} WHERE id=1",
                values,
            )

    def get_engine_state(self) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM engine_state WHERE id=1").fetchone()
            return dict(row) if row else {}

    def add_trade(self, symbol: str, side: str, qty: float, price: float, mode: str, adapter: str, order_id: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO trades (symbol, side, qty, price, mode, adapter, created_at, order_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (symbol, side, qty, price, mode, adapter, int(time.time()), order_id),
            )

    def list_trades(self, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trades ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    def list_trades_since(self, since_ts: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE created_at >= ? ORDER BY created_at DESC",
                (since_ts,),
            ).fetchall()
            return [dict(r) for r in rows]

    def compute_daily_pnl_pct(self, since_ts: int) -> float:
        trades = self.list_trades_since(since_ts)
        if not trades:
            return 0.0
        trades = list(reversed(trades))
        positions: dict[str, dict[str, float]] = {}
        realized = 0.0
        gross_notional = 0.0
        for t in trades:
            symbol = t["symbol"]
            side = t["side"]
            qty = float(t["qty"])
            price = float(t["price"])
            gross_notional += abs(qty * price)
            pos = positions.get(symbol, {"qty": 0.0, "avg": 0.0})
            if side == "BUY":
                if pos["qty"] < 0:
                    cover = min(qty, abs(pos["qty"]))
                    realized += (pos["avg"] - price) * cover
                    pos["qty"] += cover
                    qty -= cover
                if qty > 0:
                    new_qty = pos["qty"] + qty
                    pos["avg"] = ((pos["avg"] * pos["qty"]) + (price * qty)) / new_qty if new_qty else 0.0
                    pos["qty"] = new_qty
            else:
                if pos["qty"] > 0:
                    sell = min(qty, pos["qty"])
                    realized += (price - pos["avg"]) * sell
                    pos["qty"] -= sell
                    qty -= sell
                if qty > 0:
                    new_qty = pos["qty"] - qty
                    pos["avg"] = price if new_qty != 0 else 0.0
                    pos["qty"] = new_qty
            positions[symbol] = pos
        denom = gross_notional if gross_notional > 0 else 1.0
        return (realized / denom) * 100.0

    def upsert_position(self, symbol: str, qty: float, avg_price: float) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM positions WHERE symbol=?", (symbol,)
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE positions SET qty=?, avg_price=?, updated_at=? WHERE symbol=?",
                    (qty, avg_price, int(time.time()), symbol),
                )
            else:
                conn.execute(
                    "INSERT INTO positions (symbol, qty, avg_price, updated_at) VALUES (?, ?, ?, ?)",
                    (symbol, qty, avg_price, int(time.time())),
                )

    def list_positions(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM positions").fetchall()
            return [dict(r) for r in rows]

    def add_risk_event(self, reason: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO risk_events (reason, created_at) VALUES (?, ?)",
                (reason, int(time.time())),
            )

    def list_risk_events(self, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM risk_events ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
