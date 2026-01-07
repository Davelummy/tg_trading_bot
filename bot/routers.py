from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from bot import keyboards, messages
from backtest.metrics import compute_metrics
from backtest.report import render_report
from backtest.runner import run_backtest
from data.store import SQLiteStore
from engine.state import EngineStateStore
from services.config_service import ConfigService
from services.orchestrator import EngineOrchestrator


def build_router(
    orchestrator: EngineOrchestrator,
    store: SQLiteStore,
    config_service: ConfigService,
    state_store: EngineStateStore,
) -> Router:
    router = Router()
    pending_setting: dict[int, str] = {}

    @router.message(CommandStart())
    async def start_cmd(message: Message) -> None:
        await message.answer(messages.main_menu_text(), reply_markup=keyboards.main_menu())

    @router.callback_query(lambda c: c.data == "main_menu")
    async def main_menu_cb(query: CallbackQuery) -> None:
        await query.message.edit_text(messages.main_menu_text(), reply_markup=keyboards.main_menu())

    @router.callback_query(lambda c: c.data == "status")
    async def status_cb(query: CallbackQuery) -> None:
        config = config_service.load()
        state = state_store.load()
        positions = store.list_positions()
        trades = store.list_trades(limit=1)
        await query.message.edit_text(
            messages.status_text(config, state, positions, trades[0] if trades else None),
            reply_markup=keyboards.main_menu(),
        )

    @router.callback_query(lambda c: c.data == "start_paper")
    async def start_paper_cb(query: CallbackQuery) -> None:
        config_service.update("MODE", "paper")
        await orchestrator.start(chat_id=str(query.message.chat.id))
        await query.answer("Engine started (paper)")

    @router.callback_query(lambda c: c.data == "start_live")
    async def start_live_cb(query: CallbackQuery) -> None:
        await query.message.edit_text(messages.confirm_live_text(), reply_markup=keyboards.confirm_live())

    @router.callback_query(lambda c: c.data == "confirm_live")
    async def confirm_live_cb(query: CallbackQuery) -> None:
        config_service.update("MODE", "live")
        await orchestrator.start(chat_id=str(query.message.chat.id))
        await query.message.edit_text("Live trading enabled.", reply_markup=keyboards.main_menu())

    @router.callback_query(lambda c: c.data == "pause")
    async def pause_cb(query: CallbackQuery) -> None:
        await orchestrator.pause()
        await query.answer("Engine paused")

    @router.callback_query(lambda c: c.data == "backtest")
    async def backtest_cb(query: CallbackQuery) -> None:
        await query.message.answer("Backtest requested. Use /backtest CSV_PATH.")

    @router.message(Command("backtest"))
    async def backtest_cmd(message: Message) -> None:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Usage: /backtest /path/to/file.csv")
            return
        path = parts[1].strip()
        try:
            config = config_service.load()
            trades = run_backtest(path, config)
            metrics = compute_metrics(trades)
            await message.answer(render_report(metrics))
        except FileNotFoundError:
            await message.answer("CSV file not found.")
        except Exception as exc:
            await message.answer(f"Backtest failed: {exc}")

    @router.callback_query(lambda c: c.data == "settings")
    async def settings_cb(query: CallbackQuery) -> None:
        await query.message.edit_text(messages.settings_text(), reply_markup=keyboards.settings_menu())

    @router.callback_query(lambda c: c.data == "set_adapter")
    async def set_adapter_cb(query: CallbackQuery) -> None:
        await query.message.edit_text("Select adapter", reply_markup=keyboards.adapter_menu())

    @router.callback_query(lambda c: c.data.startswith("adapter:"))
    async def adapter_set_cb(query: CallbackQuery) -> None:
        adapter = query.data.split(":", 1)[1]
        config_service.update("ADAPTER", adapter)
        await query.message.edit_text(f"Adapter set to {adapter}", reply_markup=keyboards.settings_menu())

    @router.callback_query(lambda c: c.data == "set_symbols")
    async def set_symbols_cb(query: CallbackQuery) -> None:
        pending_setting[query.from_user.id] = "SYMBOLS"
        await query.message.answer(messages.prompt_text("SYMBOLS (comma-separated)"))

    @router.callback_query(lambda c: c.data == "set_timeframe")
    async def set_timeframe_cb(query: CallbackQuery) -> None:
        await query.message.edit_text("Select timeframe", reply_markup=keyboards.timeframe_menu())

    @router.callback_query(lambda c: c.data.startswith("timeframe:"))
    async def timeframe_set_cb(query: CallbackQuery) -> None:
        tf = query.data.split(":", 1)[1]
        config_service.update("TIMEFRAME", tf)
        await query.message.edit_text(f"Timeframe set to {tf}", reply_markup=keyboards.settings_menu())

    @router.callback_query(lambda c: c.data == "set_risk")
    async def set_risk_cb(query: CallbackQuery) -> None:
        await query.message.edit_text("Select risk setting", reply_markup=keyboards.risk_menu())

    @router.callback_query(lambda c: c.data.startswith("risk:"))
    async def risk_set_cb(query: CallbackQuery) -> None:
        key = query.data.split(":", 1)[1]
        pending_setting[query.from_user.id] = key
        await query.message.answer(messages.prompt_text(key))

    @router.callback_query(lambda c: c.data == "last_trades")
    async def last_trades_cb(query: CallbackQuery) -> None:
        trades = store.list_trades(limit=5)
        lines = [f"{t['symbol']} {t['side']} {t['qty']} @ {t['price']}" for t in trades] or ["none"]
        await query.message.answer("Last trades:\n" + "\n".join(lines))

    @router.callback_query(lambda c: c.data == "kill")
    async def kill_cb(query: CallbackQuery) -> None:
        await orchestrator.kill()
        await query.message.answer("Kill switch engaged. Trading halted.")

    @router.message()
    async def catch_all(message: Message) -> None:
        key = pending_setting.pop(message.from_user.id, None)
        if not key:
            return
        value = message.text.strip()
        config_service.update(key, value)
        await message.answer(f"Updated {key}")

    return router
