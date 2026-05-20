from __future__ import annotations

import asyncio
import logging
import warnings
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable

import feedparser
import httpx
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

from config import Source

log = logging.getLogger(__name__)

HTTP_TIMEOUT = 20.0
USER_AGENT = "Mozilla/5.0 (compatible; AINewsBot/1.0; +https://t.me/)"


@dataclass
class NewsItem:
    title: str
    link: str
    summary: str
    published_at: datetime
    source_name: str
    trust_tier: int


def _strip_html(raw: str) -> str:
    if not raw:
        return ""
    return BeautifulSoup(raw, "lxml").get_text(separator=" ", strip=True)


def _parse_date(entry: feedparser.FeedParserDict) -> datetime | None:
    for key in ("published", "updated", "created"):
        value = entry.get(key)
        if not value:
            continue
        try:
            dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed:
        return datetime(*parsed[:6], tzinfo=timezone.utc)
    return None


async def _fetch_feed(client: httpx.AsyncClient, source: Source) -> list[NewsItem]:
    try:
        response = await client.get(source.url, timeout=HTTP_TIMEOUT, follow_redirects=True)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("Failed to fetch %s: %s", source.name, exc)
        return []

    parsed = feedparser.parse(response.content)
    items: list[NewsItem] = []
    for entry in parsed.entries:
        link = entry.get("link", "").strip()
        title = entry.get("title", "").strip()
        if not link or not title:
            continue
        published = _parse_date(entry)
        if published is None:
            continue
        summary_raw = entry.get("summary") or entry.get("description") or ""
        items.append(
            NewsItem(
                title=title,
                link=link,
                summary=_strip_html(summary_raw)[:600],
                published_at=published,
                source_name=source.name,
                trust_tier=source.trust_tier,
            )
        )
    log.info("Fetched %d items from %s", len(items), source.name)
    return items


async def collect(sources: Iterable[Source]) -> list[NewsItem]:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml, */*"}
    async with httpx.AsyncClient(headers=headers) as client:
        tasks = [_fetch_feed(client, source) for source in sources]
        results = await asyncio.gather(*tasks, return_exceptions=False)
    return [item for batch in results for item in batch]
