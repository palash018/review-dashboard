"""SQLite storage layer (stdlib sqlite3, WAL mode).

Schema:
  reviews      - one row per guest review, stable hashed id for dedup
  scrape_runs  - audit log of every scraper run (reliability reporting)
  meta         - key/value (schema version etc.)
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

SCHEMA_VERSION = 1

_SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id               TEXT PRIMARY KEY,
    property_slug    TEXT NOT NULL,
    reviewer_name    TEXT,
    reviewer_country TEXT,
    rating           REAL,
    title            TEXT,
    positive_text    TEXT,
    negative_text    TEXT,
    review_date      TEXT,           -- ISO yyyy-mm-dd ("Reviewed: ..." date)
    stay_period      TEXT,           -- yyyy-mm (month precision)
    nights           INTEGER,
    room_type        TEXT,
    traveler_type    TEXT,
    hotel_response   TEXT,
    sentiment        TEXT,           -- positive | neutral | negative
    topics_json      TEXT,           -- [{topic, polarity, keywords}]
    classified_by    TEXT,           -- keyword | llm
    first_seen_at    TEXT NOT NULL,
    collected_at     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reviews_property_date ON reviews(property_slug, review_date);
CREATE INDEX IF NOT EXISTS idx_reviews_date ON reviews(review_date);
CREATE INDEX IF NOT EXISTS idx_reviews_sentiment ON reviews(sentiment);

CREATE TABLE IF NOT EXISTS scrape_runs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    mode           TEXT NOT NULL,
    started_at     TEXT NOT NULL,
    finished_at    TEXT,
    status         TEXT NOT NULL DEFAULT 'running',   -- running|completed|partial|failed
    properties     TEXT,                              -- json [{slug, seen, new, error}]
    reviews_seen   INTEGER DEFAULT 0,
    reviews_new    INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(db_path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # FastAPI serves sync endpoints from a threadpool; each request gets its
    # own connection, so cross-thread reuse within a request is safe.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.execute(
        "INSERT INTO meta(key, value) VALUES('schema_version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()


def review_id(slug: str, reviewer: str, review_date: str, rating: float | None,
              title: str, text_prefix: str) -> str:
    """Stable id: same review scraped twice -> same id -> upsert dedups."""
    basis = "|".join([
        slug,
        (reviewer or "").strip().lower(),
        review_date or "",
        f"{rating:g}" if rating is not None else "",
        (title or "").strip().lower(),
        (text_prefix or "").strip().lower()[:80],
    ])
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()


REVIEW_COLUMNS = (
    "id, property_slug, reviewer_name, reviewer_country, rating, title, "
    "positive_text, negative_text, review_date, stay_period, nights, "
    "room_type, traveler_type, hotel_response, sentiment, topics_json, "
    "classified_by, first_seen_at, collected_at"
)


def upsert_review(conn: sqlite3.Connection, record: dict[str, Any]) -> bool:
    """Insert review if new. Returns True when a new row was added."""
    cur = conn.execute(
        "SELECT 1 FROM reviews WHERE id = ?", (record["id"],))
    if cur.fetchone():
        return False
    values = [record.get(c) for c in REVIEW_COLUMNS.split(", ")]
    conn.execute(
        f"INSERT INTO reviews ({REVIEW_COLUMNS}) VALUES ({','.join('?' * len(values))})",
        values,
    )
    return True


def known_review_ids(conn: sqlite3.Connection) -> set[str]:
    return {r[0] for r in conn.execute("SELECT id FROM reviews")}


def start_run(conn: sqlite3.Connection, mode: str) -> int:
    # Self-heal: a stale 'running' row can only be from a dead process
    # (crash/kill), because only one scraper runs at a time.
    conn.execute(
        "UPDATE scrape_runs SET status='interrupted', "
        "finished_at=COALESCE(finished_at, ?) WHERE status='running'",
        (utc_now_iso(),))
    cur = conn.execute(
        "INSERT INTO scrape_runs(mode, started_at, status) VALUES(?, ?, 'running')",
        (mode, utc_now_iso()),
    )
    conn.commit()
    return cur.lastrowid


def finish_run(conn: sqlite3.Connection, run_id: int, status: str,
               properties: list[dict], seen: int, new: int) -> None:
    conn.execute(
        "UPDATE scrape_runs SET finished_at=?, status=?, properties=?, "
        "reviews_seen=?, reviews_new=? WHERE id=?",
        (utc_now_iso(), status, json.dumps(properties), seen, new, run_id),
    )
    conn.commit()


def export_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = []
    for r in conn.execute(f"SELECT {REVIEW_COLUMNS} FROM reviews ORDER BY review_date DESC"):
        d = dict(r)
        d["topics"] = json.loads(d.pop("topics_json") or "[]")
        rows.append(d)
    return rows


def iter_reviews(conn: sqlite3.Connection) -> Iterable[sqlite3.Row]:
    yield from conn.execute(f"SELECT {REVIEW_COLUMNS} FROM reviews ORDER BY review_date DESC")
