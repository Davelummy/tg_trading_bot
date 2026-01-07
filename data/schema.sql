CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS engine_state (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  last_candle_ts INTEGER,
  last_idempotency_key TEXT,
  last_error TEXT,
  kill_switch INTEGER DEFAULT 0,
  paused INTEGER DEFAULT 1,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  qty REAL NOT NULL,
  price REAL NOT NULL,
  mode TEXT NOT NULL,
  adapter TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  order_id TEXT
);

CREATE TABLE IF NOT EXISTS positions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  symbol TEXT NOT NULL,
  qty REAL NOT NULL,
  avg_price REAL NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reason TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
