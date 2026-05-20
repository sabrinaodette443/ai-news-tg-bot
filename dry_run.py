"""Dry-run: собирает новости и печатает 2 готовых поста в файл preview.txt БЕЗ отправки в TG."""
from __future__ import annotations

import asyncio
import logging

import config
from src.collector import collect
from src.filter import filter_ai, filter_fresh, filter_useful, rank
from src.formatter import format_post
from src.writer import get_writer

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s | %(message)s")
log = logging.getLogger("dry-run")

PREVIEW_COUNT = 2


async def main() -> None:
    log.info("Backend: %s (model: %s)", config.WRITER_BACKEND, config.OPENROUTER_MODEL)
    log.info("Collecting from %d sources...", len(config.SOURCES))
    raw = await collect(config.SOURCES)
    fresh = filter_fresh(raw, config.LOOKBACK_HOURS)
    relevant = filter_ai(fresh)
    useful = filter_useful(relevant)
    ordered = rank(useful)[:PREVIEW_COUNT]
    log.info(
        "fresh=%d, relevant=%d, useful=%d, preview=%d",
        len(fresh), len(relevant), len(useful), len(ordered),
    )

    if not ordered:
        log.warning("Nothing fresh to preview")
        return

    writer = get_writer(config.WRITER_BACKEND, config.OPENROUTER_API_KEY, config.OPENROUTER_MODEL)
    blocks: list[str] = []
    for i, item in enumerate(ordered, 1):
        body_ru = writer.write(item)
        text = format_post(item, body_ru)
        block = (
            f"\n{'=' * 60}\n"
            f"POST #{i} | source: {item.source_name} | tier: {item.trust_tier}\n"
            f"published: {item.published_at.isoformat()}\n"
            f"original title: {item.title}\n"
            f"{'=' * 60}\n"
            f"{text}\n"
            f"{'=' * 60}"
        )
        blocks.append(block)

    output = "\n".join(blocks)
    with open("preview.txt", "w", encoding="utf-8") as fh:
        fh.write(output)
    log.info("Wrote preview to preview.txt")


if __name__ == "__main__":
    asyncio.run(main())
