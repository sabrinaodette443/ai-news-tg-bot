"""Преобразование NewsItem → текст поста на русском.

Две реализации:
- GoogleWriter: дословный перевод заголовка и summary через Google Translate (fallback).
- OpenRouterWriter: LLM переписывает новость в художественный «дубляжный» стиль.
"""
from __future__ import annotations

import logging
import time
from typing import Protocol

import httpx
from deep_translator import GoogleTranslator

from src.collector import NewsItem

log = logging.getLogger(__name__)

MAX_CHUNK = 4500
RETRY_DELAYS_SEC = (5, 12, 30)

SYSTEM_PROMPT = """Ты — редактор русскоязычного Telegram-канала про нейросети. Тебе дают свежую новость про ИИ на английском (заголовок + краткое описание). Твоя задача — переписать её на русский в фирменном стиле канала.

СТИЛЬ:
Гиперболизированно-разговорный, в духе советского дубляжа «Симпсонов» и «Футурамы». Образные восклицания, провинциальный колорит, гипербола, лёгкий стёб над инфоповодом — но факты не искажай.

ПРИМЕРЫ ВОСКЛИЦАНИЙ (используй разнообразно, не один и тот же каждый раз; можно изобретать свои в том же духе):
— «Укуси меня игуана!»
— «Ставлю четвертак, что...»
— «Ну и пекло же стоит!»
— «Пройдоха Гэрри обзавидуется!»
— «Бери, пока даром раздают!»
— «Не моргнёшь — пропустишь!»
— «Чёрт меня дери!»
— «Святые угодники!»
— «У тётушки Сьюзи челюсть отвалится!»

ФОРМАТ ОТВЕТА:
1. Первая строка — короткий цепляющий вброс (восклицание + суть новости в одной фразе).
2. Пустая строка.
3. Один-два коротких абзаца с подробностями. Если в исходной новости явно перечислены фичи/числа/пункты — оформи их списком формата:
1/ ...
2/ ...
3/ ...
Используй ИМЕННО `1/`, `2/` (со слешем), а не `1.`, `1)`. Если перечня в исходнике нет — НЕ ВЫДУМЫВАЙ список, пиши обычным текстом.
4. Не вставляй ссылку — её добавят автоматически.
5. Не используй HTML, Markdown (никаких *bold*, _italic_, # заголовков), эмодзи, хэштеги, em-dash «—» в роли разделителя списка.
6. Длина всего поста — 70–180 слов.
7. Технические термины (LLM, API, GPT, agent, embedding, RAG) можно оставлять английскими, если так звучит привычнее.

КРИТИЧЕСКИ ВАЖНО ПО ФАКТАМ:
- НЕ ВЫДУМЫВАЙ конкретику: названия моделей, версий, цифры, имена людей, фичи, даты, цитаты — ничего, чего нет в заголовке или описании.
- Если в исходнике мало деталей — пиши короткий пост (70-90 слов) на основе только того, что есть. Лучше короче, чем выдумка.
- Если описание — это явная подпись к картинке (например, «Image with the words...») — игнорируй его и опирайся только на заголовок.
- Стёб и образность — приветствуются. Выдуманные технические факты — НЕТ.

ПРОЧЕЕ:
- Не повторяй заголовок дословно дважды.
- Не пиши преамбулы вроде «Вот переписанная новость:» — сразу пост.
- Отвечай ТОЛЬКО текстом поста."""


class Writer(Protocol):
    def write(self, item: NewsItem) -> str: ...


class GoogleWriter:
    def __init__(self) -> None:
        self._engine = GoogleTranslator(source="auto", target="ru")

    def _translate(self, text: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""
        try:
            if len(text) <= MAX_CHUNK:
                return self._engine.translate(text)
            chunks = [text[i : i + MAX_CHUNK] for i in range(0, len(text), MAX_CHUNK)]
            return " ".join(self._engine.translate(chunk) for chunk in chunks)
        except Exception as exc:
            log.warning("Google translate failed: %s", exc)
            return text

    def write(self, item: NewsItem) -> str:
        title_ru = self._translate(item.title).rstrip(".")
        summary_ru = self._translate(item.summary) if item.summary else ""
        if summary_ru:
            return f"{title_ru}\n\n{summary_ru}"
        return title_ru


class OpenRouterWriter:
    def __init__(self, api_key: str, model: str, fallback: Writer) -> None:
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required for OpenRouterWriter")
        self._key = api_key
        self._model = model
        self._fallback = fallback
        self._endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def _user_prompt(self, item: NewsItem) -> str:
        return (
            f"Источник: {item.source_name}\n"
            f"Заголовок: {item.title}\n"
            f"Краткое описание: {item.summary or '(нет)'}"
        )

    def _call_once(self, payload: dict, headers: dict) -> str:
        with httpx.Client(timeout=45.0) as client:
            resp = client.post(self._endpoint, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        content = data["choices"][0]["message"]["content"].strip()
        if not content:
            raise ValueError("Empty content from LLM")
        return content

    def write(self, item: NewsItem) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": self._user_prompt(item)},
            ],
            "temperature": 0.9,
            "max_tokens": 700,
        }
        headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ai-news-tg-bot",
            "X-Title": "AI News TG Bot",
        }

        last_exc: Exception | None = None
        for attempt, delay in enumerate((0, *RETRY_DELAYS_SEC)):
            if delay:
                log.info("Retrying OpenRouter after %d sec (attempt %d)", delay, attempt + 1)
                time.sleep(delay)
            try:
                return self._call_once(payload, headers)
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code in (429, 502, 503, 504):
                    continue
                break
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                last_exc = exc
                break

        log.warning(
            "OpenRouter failed after retries (%s), falling back to Google for: %s",
            last_exc, item.title[:80],
        )
        return self._fallback.write(item)


def get_writer(backend: str, openrouter_key: str, openrouter_model: str) -> Writer:
    google = GoogleWriter()
    if backend == "openrouter":
        return OpenRouterWriter(api_key=openrouter_key, model=openrouter_model, fallback=google)
    if backend == "google":
        return google
    raise ValueError(f"Unknown WRITER_BACKEND: {backend!r} (expected 'openrouter' or 'google')")
