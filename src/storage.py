from __future__ import annotations

import hashlib
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


def _ensure_dir(db_path: str) -> None:
    directory = os.path.dirname(db_path)
    if directory:
        os.makedirs(directory, exist_ok=True)


@contextmanager
def _connect(db_path: str):
    _ensure_dir(db_path)
    conn = sqlite3.connect(db_path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init(db_path: str) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posted (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                posted_at TEXT NOT NULL
            )
            """
        )


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def is_posted(db_path: str, url: str) -> bool:
    with _connect(db_path) as conn:
        cur = conn.execute("SELECT 1 FROM posted WHERE url_hash = ?", (url_hash(url),))
        return cur.fetchone() is not None


def mark_posted(db_path: str, url: str, title: str, source: str) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO posted (url_hash, url, title, source, posted_at) VALUES (?, ?, ?, ?, ?)",
            (url_hash(url), url, title, source, datetime.now(timezone.utc).isoformat()),
        )
