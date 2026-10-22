"""SQLite-backed storage for jobs, documents, and file bytes."""
from __future__ import annotations
import sqlite3
import json
import os
import uuid
from datetime import datetime
from typing import Any

DB_PATH = os.environ.get("PIXORA_DB", os.path.join(os.path.dirname(__file__), "pixora.db"))


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = _conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS files (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            mime_type TEXT DEFAULT '',
            size_bytes INTEGER DEFAULT 0,
            data BLOB,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            job_type TEXT DEFAULT 'parse',
            tier TEXT DEFAULT 'agentic',
            status TEXT DEFAULT 'queued',
            filename TEXT DEFAULT '',
            doc_type TEXT DEFAULT '',
            result TEXT,
            quality_report TEXT,
            grounding_report TEXT,
            cost_report TEXT,
            trace TEXT,
            error TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            completed_at TEXT
        );
    """)
    # Migrate: add columns if missing on older DBs
    try:
        conn.execute("SELECT filename FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE jobs ADD COLUMN filename TEXT DEFAULT ''")
    try:
        conn.execute("SELECT doc_type FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE jobs ADD COLUMN doc_type TEXT DEFAULT ''")
    try:
        conn.execute("SELECT parent_job_id FROM jobs LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE jobs ADD COLUMN parent_job_id TEXT DEFAULT ''")
    conn.commit()
    conn.close()


def save_file(filename: str, data: bytes, mime_type: str = "") -> str:
    file_id = uuid.uuid4().hex
    conn = _conn()
    conn.execute(
        "INSERT INTO files (id, filename, mime_type, size_bytes, data) VALUES (?, ?, ?, ?, ?)",
        (file_id, filename, mime_type, len(data), data),
    )
    conn.commit()
    conn.close()
    return file_id


def get_file(file_id: str) -> dict | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM files WHERE id = ?", (file_id,)).fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def save_job(job: dict) -> None:
    conn = _conn()
    conn.execute(
        """INSERT OR REPLACE INTO jobs (id, file_id, document_id, job_type, tier, status,
           result, quality_report, grounding_report, cost_report, trace, error, created_at, completed_at, filename, doc_type, parent_job_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job["id"], job.get("file_id", ""), job.get("document_id", ""),
            job.get("job_type", "parse"), job.get("tier", "agentic"), job.get("status", "queued"),
            json.dumps(job.get("result")) if job.get("result") else None,
            json.dumps(job.get("quality_report")) if job.get("quality_report") else None,
            json.dumps(job.get("grounding_report")) if job.get("grounding_report") else None,
            json.dumps(job.get("cost_report")) if job.get("cost_report") else None,
            json.dumps(job.get("trace")) if job.get("trace") else None,
            job.get("error"),
            job.get("created_at", datetime.now().isoformat()),
            job.get("completed_at"),
            job.get("filename", ""),
            job.get("doc_type", ""),
            job.get("parent_job_id", ""),
        ),
    )
    conn.commit()
    conn.close()


def get_job(job_id: str) -> dict | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    for key in ("result", "quality_report", "grounding_report", "cost_report", "trace"):
        if d.get(key):
            d[key] = json.loads(d[key])
    return d


def list_jobs(limit: int = 100) -> list[dict]:
    conn = _conn()
    rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    results = []
    for row in rows:
        d = dict(row)
        for key in ("result", "quality_report", "grounding_report", "cost_report", "trace"):
            if d.get(key):
                d[key] = json.loads(d[key])
        results.append(d)
    return results


def update_job(job_id: str, **fields) -> None:
    conn = _conn()
    for key in ("result", "quality_report", "grounding_report", "cost_report", "trace"):
        if key in fields and fields[key] is not None and not isinstance(fields[key], str):
            fields[key] = json.dumps(fields[key])
    sets = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [job_id]
    conn.execute(f"UPDATE jobs SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def delete_job(job_id: str) -> bool:
    conn = _conn()
    cur = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def job_stats() -> dict:
    conn = _conn()
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM jobs GROUP BY status"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    conn.close()
    stats = {row["status"]: row["cnt"] for row in rows}
    stats["total"] = total
    return stats


init_db()
