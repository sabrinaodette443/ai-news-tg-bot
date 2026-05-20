from __future__ import annotations

import html
import re

from src.collector import NewsItem

_MULTI_NEWLINE = re.compile(r"\n{3,}")


def _escape(text: str) -> str:
    return html.escape(text or "", quote=False)


def _normalize(text: str) -> str:
    text = (text or "").strip()
    return _MULTI_NEWLINE.sub("\n\n", text)


def format_post(item: NewsItem, body_ru: str) -> str:
    body = _escape(_normalize(body_ru))
    link = item.link
    if not body:
        return f"ссылка: {link}"
    return f"{body}\n\nссылка: {link}"
