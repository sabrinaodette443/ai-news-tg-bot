from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from config import AI_KEYWORDS
from src.collector import NewsItem

MIN_USEFUL_SUMMARY_CHARS = 120

_IMAGE_ALT_PREFIXES = re.compile(
    r"^(image|photo|picture|illustration|graphic|screenshot|изображение|фото)\b",
    re.IGNORECASE,
)


def _matches_ai(item: NewsItem) -> bool:
    haystack = f"{item.title}\n{item.summary}".lower()
    return any(keyword in haystack for keyword in AI_KEYWORDS)


def _summary_is_useful(summary: str) -> bool:
    """Считаем summary бесполезным, если он слишком короткий или это alt-текст к картинке."""
    s = (summary or "").strip()
    if not s:
        return False
    if _IMAGE_ALT_PREFIXES.match(s) and len(s) < 300:
        return False
    return len(s) >= MIN_USEFUL_SUMMARY_CHARS


def filter_fresh(items: list[NewsItem], lookback_hours: int) -> list[NewsItem]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    return [item for item in items if item.published_at >= cutoff]


def filter_ai(items: list[NewsItem]) -> list[NewsItem]:
    return [item for item in items if _matches_ai(item)]


def filter_useful(items: list[NewsItem]) -> list[NewsItem]:
    """Отсеиваем новости с пустым/мусорным summary, чтобы LLM не выдумывал контент."""
    return [item for item in items if _summary_is_useful(item.summary)]


def rank(items: list[NewsItem]) -> list[NewsItem]:
    return sorted(items, key=lambda i: (i.trust_tier, -i.published_at.timestamp()))
