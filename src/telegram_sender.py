from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramRetryAfter, TelegramAPIError

log = logging.getLogger(__name__)

SEND_DELAY_SECONDS = 3.0


class TelegramSender:
    def __init__(self, token: str, channel_id: str) -> None:
        self._bot = Bot(
            token=token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=False),
        )
        self._channel_id = channel_id

    async def send(self, html_text: str) -> bool:
        try:
            await self._bot.send_message(chat_id=self._channel_id, text=html_text)
            return True
        except TelegramRetryAfter as exc:
            log.warning("Rate limited, sleeping %s s", exc.retry_after)
            await asyncio.sleep(exc.retry_after + 1)
            return await self.send(html_text)
        except TelegramAPIError as exc:
            log.error("Failed to send message: %s", exc)
            return False

    async def close(self) -> None:
        await self._bot.session.close()
