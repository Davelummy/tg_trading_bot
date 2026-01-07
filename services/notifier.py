from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

from loguru import logger


@dataclass
class Alert:
    chat_id: str
    text: str


class Notifier:
    def __init__(self) -> None:
        self.queue: asyncio.Queue[Alert] = asyncio.Queue()
        self._task: Optional[asyncio.Task] = None

    async def start(self, bot) -> None:
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(bot))

    async def _run(self, bot) -> None:
        while True:
            alert = await self.queue.get()
            try:
                await bot.send_message(alert.chat_id, alert.text)
            except Exception as exc:
                logger.exception("Failed to send alert: {}", exc)
            finally:
                self.queue.task_done()

    async def send(self, chat_id: str, text: str) -> None:
        await self.queue.put(Alert(chat_id=chat_id, text=text))
