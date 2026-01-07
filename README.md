# Telegram Trading Bot

Production-grade Telegram control panel for a server-side trading engine that supports backtest, paper, and live trading on Binance Spot and MT5.

## Features
- Admin-only Telegram UI with inline menus, confirmations, throttling
- Modes: BACKTEST, PAPER, LIVE
- Adapters: Paper, Binance Spot, MT5
- Restart-safe state, idempotency, kill switch, circuit breaker
- Async notifier queue for alerts

## BotFather Setup
1. Create a new bot in BotFather.
2. Copy the token into `.env` as `TELEGRAM_BOT_TOKEN`.
3. Add admin IDs to `ADMIN_TELEGRAM_IDS`.

## Local Run (Polling)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python -m bot.app
```

## Production Run (Webhook)
- Use an HTTPS reverse proxy (Caddy, Nginx) with a valid TLS cert.
- Configure `setWebhook` in BotFather or via Telegram API.
- Run the bot behind your proxy and ensure the webhook URL is reachable.

## Docker
```bash
docker compose up --build
```

## MT5 Windows Setup
1. Install MetaTrader 5 terminal on Windows.
2. Log into your broker account in MT5.
3. Install Python 3.11+ and `pip install MetaTrader5` (Windows-only package).
4. Run this bot on the same Windows machine (or expose a bridge).

### Linux to Windows Bridge (Skeleton)
- `adapters/mt5_bridge.py` expects an HTTP service that exposes:
  - `GET /candles?symbol=EURUSD&tf=1m&limit=200`
  - `GET /positions`
  - `GET /spread?symbol=EURUSD`
  - `POST /order`
- Implement this in a Windows-side service or EA bridge, then use it as the adapter.

## Safety
- Admin-only controls via `ADMIN_TELEGRAM_IDS`
- Live confirmation required
- Kill switch stored in DB and enforced by engine
- Circuit breaker on max daily loss

## Disclaimer
Educational use only. Not financial advice.
