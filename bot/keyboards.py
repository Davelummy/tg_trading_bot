from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="✅ Status", callback_data="status")],
        [InlineKeyboardButton(text="▶️ Start (Paper)", callback_data="start_paper")],
        [InlineKeyboardButton(text="🚀 Start (Live)", callback_data="start_live")],
        [InlineKeyboardButton(text="⏸ Pause", callback_data="pause")],
        [InlineKeyboardButton(text="🧪 Backtest", callback_data="backtest")],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton(text="🧾 Last Trades", callback_data="last_trades")],
        [InlineKeyboardButton(text="🛑 Emergency Stop", callback_data="kill")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_live() -> InlineKeyboardMarkup:
    buttons = [[InlineKeyboardButton(text="CONFIRM LIVE", callback_data="confirm_live")]]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def settings_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Adapter", callback_data="set_adapter")],
        [InlineKeyboardButton(text="Symbols", callback_data="set_symbols")],
        [InlineKeyboardButton(text="Timeframe", callback_data="set_timeframe")],
        [InlineKeyboardButton(text="Risk", callback_data="set_risk")],
        [InlineKeyboardButton(text="Back", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def adapter_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="paper", callback_data="adapter:paper")],
        [InlineKeyboardButton(text="binance", callback_data="adapter:binance")],
        [InlineKeyboardButton(text="mt5", callback_data="adapter:mt5")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def timeframe_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="1m", callback_data="timeframe:1m")],
        [InlineKeyboardButton(text="5m", callback_data="timeframe:5m")],
        [InlineKeyboardButton(text="15m", callback_data="timeframe:15m")],
        [InlineKeyboardButton(text="1h", callback_data="timeframe:1h")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def risk_menu() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="RISK_PER_TRADE_PCT", callback_data="risk:RISK_PER_TRADE_PCT")],
        [InlineKeyboardButton(text="MAX_DAILY_LOSS_PCT", callback_data="risk:MAX_DAILY_LOSS_PCT")],
        [InlineKeyboardButton(text="MAX_TRADES_PER_DAY", callback_data="risk:MAX_TRADES_PER_DAY")],
        [InlineKeyboardButton(text="MAX_OPEN_POSITIONS", callback_data="risk:MAX_OPEN_POSITIONS")],
        [InlineKeyboardButton(text="MAX_SPREAD", callback_data="risk:MAX_SPREAD")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
