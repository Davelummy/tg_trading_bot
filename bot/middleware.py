from __future__ import annotations

import time
from typing import Callable, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from services.config_service import BotSettings


def _is_admin(user_id: int, settings: BotSettings) -> bool:
    ids = {int(x.strip()) for x in settings.ADMIN_TELEGRAM_IDS.split(",") if x.strip()}
    return user_id in ids


def _is_allowed(user_id: int, settings: BotSettings) -> bool:
    if settings.ALLOW_ALL_USERS:
        return True
    return _is_admin(user_id, settings)


class AdminOnlyMiddleware(BaseMiddleware):
    def __init__(self, settings: BotSettings) -> None:
        self.settings = settings

    async def __call__(self, handler: Callable, event, data) -> Awaitable:
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        if user and not _is_allowed(user.id, self.settings):
            if isinstance(event, Message):
                await event.answer("Access denied. This bot is admin-only.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Access denied. This bot is admin-only.", show_alert=True)
            return
        return await handler(event, data)


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, cooldown: float = 1.0) -> None:
        self.cooldown = cooldown
        self._last: dict[int, float] = {}

    async def __call__(self, handler: Callable, event, data) -> Awaitable:
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        if user_id:
            now = time.time()
            last = self._last.get(user_id, 0)
            if now - last < self.cooldown:
                if isinstance(event, CallbackQuery):
                    await event.answer("Slow down.")
                return
            self._last[user_id] = now
        return await handler(event, data)
