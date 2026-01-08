from __future__ import annotations

from engine.state import EngineState
from services.config_service import RuntimeConfig


def main_menu_text() -> str:
    return "Trading Bot Control Panel"


def status_text(config: RuntimeConfig, state: EngineState, positions: list[dict], last_trade: dict | None) -> str:
    positions_summary = ", ".join([f"{p['symbol']} {p['qty']} @ {p['avg_price']}" for p in positions]) or "none"
    trade_summary = (
        f"{last_trade['symbol']} {last_trade['side']} {last_trade['qty']} @ {last_trade['price']}"
        if last_trade
        else "none"
    )
    return (
        f"Mode: {config.mode.upper()}\n"
        f"Running: {'no' if state.paused else 'yes'}\n"
        f"Adapter: {config.adapter}\n"
        f"Last tick: {state.last_candle_ts or 'n/a'}\n"
        f"Open positions: {positions_summary}\n"
        f"Last trade: {trade_summary}\n"
        f"Kill switch: {'ON' if state.kill_switch else 'OFF'}\n"
        f"Last error: {state.last_error or 'none'}"
    )


def access_denied_text() -> str:
    return "Access denied. This bot is admin-only."


def confirm_live_text() -> str:
    return "LIVE trading will place real orders. Click CONFIRM LIVE to proceed."


def settings_text() -> str:
    return "Settings: choose what to update."


def prompt_text(label: str) -> str:
    return f"Send new value for {label}."
