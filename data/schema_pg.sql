CREATE TABLE IF NOT EXISTS users (
  user_id BIGINT PRIMARY KEY,
  username TEXT,
  created_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_settings (
  user_id BIGINT NOT NULL,
  key TEXT NOT NULL,
  value TEXT NOT NULL,
  PRIMARY KEY (user_id, key)
);

CREATE TABLE IF NOT EXISTS credentials (
  user_id BIGINT NOT NULL,
  adapter TEXT NOT NULL,
  data_encrypted TEXT NOT NULL,
  created_at BIGINT NOT NULL,
  updated_at BIGINT NOT NULL,
  PRIMARY KEY (user_id, adapter)
);

CREATE TABLE IF NOT EXISTS engine_state (
  user_id BIGINT PRIMARY KEY,
  last_candle_ts BIGINT,
  last_error TEXT,
  kill_switch BOOLEAN DEFAULT FALSE,
  paused BOOLEAN DEFAULT TRUE,
  updated_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS trades (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  qty DOUBLE PRECISION NOT NULL,
  price DOUBLE PRECISION NOT NULL,
  mode TEXT NOT NULL,
  adapter TEXT NOT NULL,
  created_at BIGINT NOT NULL,
  order_id TEXT
);

CREATE TABLE IF NOT EXISTS positions (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  symbol TEXT NOT NULL,
  qty DOUBLE PRECISION NOT NULL,
  avg_price DOUBLE PRECISION NOT NULL,
  updated_at BIGINT NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_events (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL,
  reason TEXT NOT NULL,
  created_at BIGINT NOT NULL
);
