from __future__ import annotations

import asyncio
import logging
import sys

import config
from src import storage
from src.collector import NewsItem, collect
from src.filter import filter_ai, filter_fresh, filter_useful, rank
from src.formatter import format_post
from src.telegram_sender import SEND_DELAY_SECONDS, TelegramSender
from src.writer import get_writer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(name)s | %(message)s",
)
log = logging.getLogger("ai-news-bot")


def _validate_env() -> None:
    missing = [name for name in ("BOT_TOKEN", "CHANNEL_ID") if not getattr(config, name)]
    if missing:
        raise SystemExit(f"Missing required env vars: {', '.join(missing)}")
    if config.WRITER_BACKEND == "openrouter" and not config.OPENROUTER_API_KEY:
        raise SystemExit("WRITER_BACKEND=openrouter, but OPENROUTER_API_KEY is empty")


def _dedupe(items: list[NewsItem]) -> list[NewsItem]:
    return [item for item in items if not storage.is_posted(config.DB_PATH, item.link)]


async def run() -> int:
    _validate_env()
    storage.init(config.DB_PATH)

    log.info("Collecting from %d sources...", len(config.SOURCES))
    raw = await collect(config.SOURCES)
    log.info("Collected %d items total", len(raw))

    fresh = filter_fresh(raw, config.LOOKBACK_HOURS)
    relevant = filter_ai(fresh)
    useful = filter_useful(relevant)
    new_items = _dedupe(useful)
    ordered = rank(new_items)[: config.MAX_POSTS_PER_RUN]

    log.info(
        "Pipeline: fresh=%d, relevant=%d, useful=%d, new=%d, to_publish=%d",
        len(fresh), len(relevant), len(useful), len(new_items), len(ordered),
    )

    if not ordered:
        log.info("Nothing to publish, exiting cleanly")
        return 0

    writer = get_writer(config.WRITER_BACKEND, config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    sender = TelegramSender(config.BOT_TOKEN, config.CHANNEL_ID)
    sent_count = 0

    try:
        for item in ordered:
            body_ru = writer.write(item)
            text = format_post(item, body_ru)
            ok = await sender.send(text)
            if ok:
                storage.mark_posted(config.DB_PATH, item.link, item.title, item.source_name)
                sent_count += 1
            await asyncio.sleep(SEND_DELAY_SECONDS)
    finally:
        await sender.close()

    log.info("Published %d/%d items", sent_count, len(ordered))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))
