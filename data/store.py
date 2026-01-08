from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


class BaseStore:
    def ensure_user(self, user_id: int, username: str | None) -> None:
        raise NotImplementedError

    def set_setting(self, user_id: int, key: str, value: Any) -> None:
        raise NotImplementedError

    def get_setting(self, user_id: int, key: str, default: Any = None) -> Any:
        raise NotImplementedError

    def set_engine_state(self, user_id: int, **kwargs: Any) -> None:
        raise NotImplementedError

    def get_engine_state(self, user_id: int) -> dict[str, Any]:
        raise NotImplementedError

    def add_trade(self, user_id: int, symbol: str, side: str, qty: float, price: float, mode: str, adapter: str, order_id: str | None) -> None:
        raise NotImplementedError

    def list_trades(self, user_id: int, limit: int = 5) -> list[dict[str, Any]]:
        raise NotImplementedError

    def list_trades_since(self, user_id: int, since_ts: int) -> list[dict[str, Any]]:
        raise NotImplementedError

    def compute_daily_pnl_pct(self, user_id: int, since_ts: int) -> float:
        raise NotImplementedError

    def upsert_position(self, user_id: int, symbol: str, qty: float, avg_price: float) -> None:
        raise NotImplementedError

    def list_positions(self, user_id: int) -> list[dict[str, Any]]:
        raise NotImplementedError

    def add_risk_event(self, user_id: int, reason: str) -> None:
        raise NotImplementedError

    def list_risk_events(self, user_id: int, limit: int = 5) -> list[dict[str, Any]]:
        raise NotImplementedError

    def set_credentials(self, user_id: int, adapter: str, data_encrypted: str) -> None:
        raise NotImplementedError

    def get_credentials(self, user_id: int, adapter: str) -> str | None:
        raise NotImplementedError


class SQLiteStore(BaseStore):
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
            self._migrate_sqlite(conn)
            conn.executescript(schema_path.read_text())

    def _table_has_column(self, conn: sqlite3.Connection, table: str, column: str) -> bool:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return any(r["name"] == column for r in rows)

    def _table_exists(self, conn: sqlite3.Connection, table: str) -> bool:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()
        return bool(row)

    def _migrate_sqlite(self, conn: sqlite3.Connection) -> None:
        if self._table_exists(conn, "engine_state") and not self._table_has_column(conn, "engine_state", "user_id"):
            conn.execute(
                "CREATE TABLE engine_state_new (user_id INTEGER PRIMARY KEY, last_candle_ts INTEGER, last_error TEXT, kill_switch INTEGER DEFAULT 0, paused INTEGER DEFAULT 1, updated_at INTEGER NOT NULL)"
            )
            row = conn.execute("SELECT last_candle_ts, last_error, kill_switch, paused, updated_at FROM engine_state WHERE id=1").fetchone()
            if row:
                conn.execute(
                    "INSERT INTO engine_state_new (user_id, last_candle_ts, last_error, kill_switch, paused, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (1, row["last_candle_ts"], row["last_error"], row["kill_switch"], row["paused"], row["updated_at"]),
                )
            conn.execute("DROP TABLE engine_state")
            conn.execute("ALTER TABLE engine_state_new RENAME TO engine_state")

        if self._table_exists(conn, "settings"):
            if not self._table_exists(conn, "user_settings"):
                conn.execute(
                    "CREATE TABLE user_settings (user_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY (user_id, key))"
                )
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            for row in rows:
                conn.execute(
                    "INSERT OR REPLACE INTO user_settings (user_id, key, value) VALUES (?, ?, ?)",
                    (1, row["key"], row["value"]),
                )
            conn.execute("DROP TABLE settings")

        for table in ("trades", "positions", "risk_events"):
            if self._table_exists(conn, table) and not self._table_has_column(conn, table, "user_id"):
                conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER DEFAULT 1")

    def ensure_user(self, user_id: int, username: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (user_id, username, created_at) VALUES (?, ?, ?)",
                (user_id, username, int(time.time())),
            )
            conn.execute(
                "INSERT OR IGNORE INTO engine_state (user_id, updated_at) VALUES (?, ?)",
                (user_id, int(time.time())),
            )

    def set_setting(self, user_id: int, key: str, value: Any) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO user_settings (user_id, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT(user_id, key) DO UPDATE SET value=excluded.value",
                (user_id, key, json.dumps(value)),
            )

    def get_setting(self, user_id: int, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM user_settings WHERE user_id=? AND key=?",
                (user_id, key),
            ).fetchone()
            if not row:
                return default
            return json.loads(row["value"])

    def set_engine_state(self, user_id: int, **kwargs: Any) -> None:
        values = list(kwargs.values())
        with self._connect() as conn:
            conn.execute(
                f"UPDATE engine_state SET {', '.join([f'{k}=?' for k in kwargs.keys()])} WHERE user_id=?",
                values + [user_id],
            )

    def get_engine_state(self, user_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM engine_state WHERE user_id=?",
                (user_id,),
            ).fetchone()
            return dict(row) if row else {}

    def add_trade(self, user_id: int, symbol: str, side: str, qty: float, price: float, mode: str, adapter: str, order_id: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO trades (user_id, symbol, side, qty, price, mode, adapter, created_at, order_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (user_id, symbol, side, qty, price, mode, adapter, int(time.time()), order_id),
            )

    def list_trades(self, user_id: int, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_trades_since(self, user_id: int, since_ts: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE user_id=? AND created_at >= ? ORDER BY created_at DESC",
                (user_id, since_ts),
            ).fetchall()
            return [dict(r) for r in rows]

    def compute_daily_pnl_pct(self, user_id: int, since_ts: int) -> float:
        trades = self.list_trades_since(user_id, since_ts)
        return _compute_pnl_pct(trades)

    def upsert_position(self, user_id: int, symbol: str, qty: float, avg_price: float) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM positions WHERE user_id=? AND symbol=?",
                (user_id, symbol),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE positions SET qty=?, avg_price=?, updated_at=? WHERE user_id=? AND symbol=?",
                    (qty, avg_price, int(time.time()), user_id, symbol),
                )
            else:
                conn.execute(
                    "INSERT INTO positions (user_id, symbol, qty, avg_price, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, symbol, qty, avg_price, int(time.time())),
                )

    def list_positions(self, user_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM positions WHERE user_id=?",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def add_risk_event(self, user_id: int, reason: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO risk_events (user_id, reason, created_at) VALUES (?, ?, ?)",
                (user_id, reason, int(time.time())),
            )

    def list_risk_events(self, user_id: int, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM risk_events WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def set_credentials(self, user_id: int, adapter: str, data_encrypted: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO credentials (user_id, adapter, data_encrypted, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT(user_id, adapter) DO UPDATE SET data_encrypted=excluded.data_encrypted, updated_at=excluded.updated_at",
                (user_id, adapter, data_encrypted, int(time.time()), int(time.time())),
            )

    def get_credentials(self, user_id: int, adapter: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data_encrypted FROM credentials WHERE user_id=? AND adapter=?",
                (user_id, adapter),
            ).fetchone()
            return row["data_encrypted"] if row else None


class PostgresStore(BaseStore):
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self._ensure_schema()

    def _connect(self):
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def _ensure_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema_pg.sql")
        with self._connect() as conn:
            statements = [s.strip() for s in schema_path.read_text().split(";") if s.strip()]
            for stmt in statements:
                conn.execute(stmt)

    def ensure_user(self, user_id: int, username: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO users (user_id, username, created_at) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                (user_id, username, int(time.time())),
            )
            conn.execute(
                "INSERT INTO engine_state (user_id, updated_at) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                (user_id, int(time.time())),
            )

    def set_setting(self, user_id: int, key: str, value: Any) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO user_settings (user_id, key, value) VALUES (%s, %s, %s) "
                "ON CONFLICT (user_id, key) DO UPDATE SET value=excluded.value",
                (user_id, key, json.dumps(value)),
            )

    def get_setting(self, user_id: int, key: str, default: Any = None) -> Any:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value FROM user_settings WHERE user_id=%s AND key=%s",
                (user_id, key),
            ).fetchone()
            if not row:
                return default
            return json.loads(row[0])

    def set_engine_state(self, user_id: int, **kwargs: Any) -> None:
        values = list(kwargs.values())
        with self._connect() as conn:
            conn.execute(
                f"UPDATE engine_state SET {', '.join([f'{k}=%s' for k in kwargs.keys()])} WHERE user_id=%s",
                values + [user_id],
            )

    def get_engine_state(self, user_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id, last_candle_ts, last_error, kill_switch, paused, updated_at FROM engine_state WHERE user_id=%s",
                (user_id,),
            ).fetchone()
            return dict(row) if row else {}

    def add_trade(self, user_id: int, symbol: str, side: str, qty: float, price: float, mode: str, adapter: str, order_id: str | None) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO trades (user_id, symbol, side, qty, price, mode, adapter, created_at, order_id) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (user_id, symbol, side, qty, price, mode, adapter, int(time.time()), order_id),
            )

    def list_trades(self, user_id: int, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE user_id=%s ORDER BY created_at DESC LIMIT %s",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def list_trades_since(self, user_id: int, since_ts: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE user_id=%s AND created_at >= %s ORDER BY created_at DESC",
                (user_id, since_ts),
            ).fetchall()
            return [dict(r) for r in rows]

    def compute_daily_pnl_pct(self, user_id: int, since_ts: int) -> float:
        trades = self.list_trades_since(user_id, since_ts)
        return _compute_pnl_pct(trades)

    def upsert_position(self, user_id: int, symbol: str, qty: float, avg_price: float) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM positions WHERE user_id=%s AND symbol=%s",
                (user_id, symbol),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE positions SET qty=%s, avg_price=%s, updated_at=%s WHERE user_id=%s AND symbol=%s",
                    (qty, avg_price, int(time.time()), user_id, symbol),
                )
            else:
                conn.execute(
                    "INSERT INTO positions (user_id, symbol, qty, avg_price, updated_at) VALUES (%s, %s, %s, %s, %s)",
                    (user_id, symbol, qty, avg_price, int(time.time())),
                )

    def list_positions(self, user_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM positions WHERE user_id=%s",
                (user_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def add_risk_event(self, user_id: int, reason: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO risk_events (user_id, reason, created_at) VALUES (%s, %s, %s)",
                (user_id, reason, int(time.time())),
            )

    def list_risk_events(self, user_id: int, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM risk_events WHERE user_id=%s ORDER BY created_at DESC LIMIT %s",
                (user_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def set_credentials(self, user_id: int, adapter: str, data_encrypted: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO credentials (user_id, adapter, data_encrypted, created_at, updated_at) "
                "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (user_id, adapter) DO UPDATE SET data_encrypted=excluded.data_encrypted, updated_at=excluded.updated_at",
                (user_id, adapter, data_encrypted, int(time.time()), int(time.time())),
            )

    def get_credentials(self, user_id: int, adapter: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT data_encrypted FROM credentials WHERE user_id=%s AND adapter=%s",
                (user_id, adapter),
            ).fetchone()
            return row[0] if row else None


def _compute_pnl_pct(trades: list[dict[str, Any]]) -> float:
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


def create_store(database_url: str | None, sqlite_path: str) -> BaseStore:
    if database_url:
        return PostgresStore(database_url)
    return SQLiteStore(sqlite_path)
