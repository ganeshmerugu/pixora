"""Document hash cache for deduplication.

SHA-256 of input bytes -> cached extraction result.
SQLite-backed with TTL expiration. Short-circuits the entire pipeline
for duplicate documents.
"""
from __future__ import annotations
import hashlib
import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Any

DB_PATH = os.environ.get("PIXORA_CACHE_DB", os.path.join(os.path.dirname(__file__), "pixora_cache.db"))

_DEFAULT_TTL_HOURS = 24


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_cache_db() -> None:
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS document_cache (
            hash TEXT PRIMARY KEY,
            result TEXT NOT NULL,
            filename TEXT DEFAULT '',
            doc_type TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            expires_at TEXT NOT NULL,
            hit_count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


_init_cache_db()


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class DocumentCache:
    def __init__(self, ttl_hours: float = _DEFAULT_TTL_HOURS):
        self.ttl_hours = ttl_hours

    def get(self, file_bytes: bytes) -> dict[str, Any] | None:
        h = _hash_bytes(file_bytes)
        conn = _conn()
        row = conn.execute(
            "SELECT result, expires_at FROM document_cache WHERE hash = ?", (h,)
        ).fetchone()

        if not row:
            conn.close()
            return None

        expires = datetime.fromisoformat(row["expires_at"])
        if datetime.now() > expires:
            conn.execute("DELETE FROM document_cache WHERE hash = ?", (h,))
            conn.commit()
            conn.close()
            return None

        conn.execute(
            "UPDATE document_cache SET hit_count = hit_count + 1 WHERE hash = ?", (h,)
        )
        conn.commit()
        conn.close()
        return json.loads(row["result"])

    def put(
        self,
        file_bytes: bytes,
        result: dict[str, Any],
        filename: str = "",
        doc_type: str = "",
        ttl_hours: float | None = None,
    ) -> str:
        h = _hash_bytes(file_bytes)
        ttl = ttl_hours or self.ttl_hours
        expires = (datetime.now() + timedelta(hours=ttl)).isoformat()

        conn = _conn()
        conn.execute(
            """INSERT OR REPLACE INTO document_cache
               (hash, result, filename, doc_type, expires_at, hit_count)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (h, json.dumps(result), filename, doc_type, expires),
        )
        conn.commit()
        conn.close()
        return h

    def invalidate(self, file_bytes: bytes) -> bool:
        h = _hash_bytes(file_bytes)
        conn = _conn()
        cur = conn.execute("DELETE FROM document_cache WHERE hash = ?", (h,))
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    def clear_expired(self) -> int:
        conn = _conn()
        now = datetime.now().isoformat()
        cur = conn.execute("DELETE FROM document_cache WHERE expires_at < ?", (now,))
        conn.commit()
        count = cur.rowcount
        conn.close()
        return count

    def stats(self) -> dict[str, Any]:
        conn = _conn()
        total = conn.execute("SELECT COUNT(*) FROM document_cache").fetchone()[0]
        now = datetime.now().isoformat()
        active = conn.execute(
            "SELECT COUNT(*) FROM document_cache WHERE expires_at >= ?", (now,)
        ).fetchone()[0]
        total_hits = conn.execute(
            "SELECT COALESCE(SUM(hit_count), 0) FROM document_cache"
        ).fetchone()[0]
        conn.close()
        return {"total_entries": total, "active_entries": active, "total_hits": total_hits}
