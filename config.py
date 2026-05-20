from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    trust_tier: int


SOURCES: list[Source] = [
    Source("OpenAI",            "https://openai.com/blog/rss.xml",                                     1),
    Source("Anthropic",         "https://www.anthropic.com/news/rss.xml",                              1),
    Source("Google DeepMind",   "https://deepmind.google/blog/rss.xml",                                1),
    Source("Google AI Blog",    "https://blog.google/technology/ai/rss/",                              1),
    Source("Hugging Face",      "https://huggingface.co/blog/feed.xml",                                1),
    Source("Meta AI",           "https://ai.meta.com/blog/rss/",                                       1),
    Source("Microsoft AI",      "https://blogs.microsoft.com/ai/feed/",                                1),
    Source("MIT Tech Review",   "https://www.technologyreview.com/topic/artificial-intelligence/feed", 2),
    Source("The Verge AI",      "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",   2),
    Source("TechCrunch AI",     "https://techcrunch.com/category/artificial-intelligence/feed/",       2),
    Source("VentureBeat AI",    "https://venturebeat.com/category/ai/feed/",                           2),
    Source("Ars Technica AI",   "https://arstechnica.com/ai/feed/",                                    2),
]

AI_KEYWORDS: tuple[str, ...] = (
    "ai", "artificial intelligence", "machine learning", "ml ",
    "neural", "llm", "gpt", "claude", "gemini", "llama",
    "openai", "anthropic", "deepmind", "mistral", "perplexity",
    "transformer", "diffusion", "stable diffusion", "midjourney",
    "agent", "agents", "rag", "fine-tun", "embedding",
    "chatgpt", "copilot", "model", "inference", "training",
)

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")
MAX_POSTS_PER_RUN: int = int(os.getenv("MAX_POSTS_PER_RUN", "8"))
LOOKBACK_HOURS: int = int(os.getenv("LOOKBACK_HOURS", "24"))

WRITER_BACKEND: str = os.getenv("WRITER_BACKEND", "openrouter")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "openai/gpt-oss-120b:free")

DB_PATH: str = os.path.join(os.path.dirname(__file__), "data", "posts.db")
