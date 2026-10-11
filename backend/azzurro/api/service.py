"""Aggregation/queries powering the dashboard API (pure functions, no HTTP)."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from typing import Any

WEEK_START_SQL = "date(review_date, '-6 days', 'weekday 1')"


def week_bounds(d: date) -> tuple[date, date]:
    """Monday..Sunday of the week containing d."""
    monday = d - timedelta(days=d.weekday())
    return monday, monday + timedelta(days=6)


def _clamp_filters(slugs: list[str] | None) -> list[str]:
    from ..config import PROPERTIES
    if not slugs:
        return list(PROPERTIES)
    return [s for s in slugs if s in PROPERTIES]


def _sentiment_counts(conn: sqlite3.Connection, where: str, params: list
                      ) -> dict[str, int]:
    row = conn.execute(
        f"SELECT COUNT(*) FILTER (WHERE sentiment='positive'), "
        f"COUNT(*) FILTER (WHERE sentiment='neutral'), "
        f"COUNT(*) FILTER (WHERE sentiment='negative'), COUNT(*) "
        f"FROM reviews WHERE {where}", params).fetchone()
    return {"positive": row[0] or 0, "neutral": row[1] or 0,
            "negative": row[2] or 0, "total": row[3] or 0}


def kpis(conn: sqlite3.Connection, property: str | None,
         start: date, end: date) -> dict[str, Any]:
    """KPIs for the selected period vs the previous period of equal length.

    With start..end = the current calendar week this is exactly
    "this week vs previous week". Longer selections (All time, Last 4 weeks)
    compare against the immediately preceding window of the same length;
    when no data exists there, deltas are null ("no data for comparison").
    """
    from ..config import PROPERTIES
    days = (end - start).days + 1
    pstart, pend = start - timedelta(days=days), start - timedelta(days=1)
    slugs = _clamp_filters([property] if property else None)
    ph = ",".join("?" * len(slugs))
    range_where = f"property_slug IN ({ph}) AND review_date >= ? AND review_date <= ?"

    def period_stats(a: date, b: date) -> dict[str, Any]:
        params = [*slugs, a.isoformat(), b.isoformat()]
        avg = conn.execute(
            f"SELECT ROUND(AVG(rating),2) FROM reviews WHERE {range_where}",
            params).fetchone()[0]
        counts = _sentiment_counts(conn, range_where, params)
        return {
            "avg_rating": avg,
            "reviews": counts["total"],
            "sentiment": counts,
            "pct_negative": (round(100 * counts["negative"] / counts["total"], 1)
                             if counts["total"] else None),
        }

    cur = period_stats(start, end)
    prev = period_stats(pstart, pend)
    has_prev = prev["reviews"] > 0

    if has_prev:
        delta = {
            "avg_rating": None if (cur["avg_rating"] is None or
                                   prev["avg_rating"] is None)
            else round(cur["avg_rating"] - prev["avg_rating"], 2),
            "reviews": cur["reviews"] - prev["reviews"],
            "pct_negative": None if (cur["pct_negative"] is None or
                                     prev["pct_negative"] is None)
            else round(cur["pct_negative"] - prev["pct_negative"], 1),
        }
    else:
        delta = {"avg_rating": None, "reviews": None, "pct_negative": None}

    return {
        "period": {"start": start.isoformat(), "end": end.isoformat(),
                   "days": days},
        "prev_period": {"start": pstart.isoformat(), "end": pend.isoformat()},
        "current": cur,
        "previous": {**prev, "has_data": has_prev},
        "delta": delta,
        "property_count": len(PROPERTIES),
    }


def property_breakdown(conn: sqlite3.Connection, property: str | None,
                       start: date, end: date) -> list[dict[str, Any]]:
    """Per-property: this-period vs previous-period (same length) stats."""
    from ..config import PROPERTIES
    days = (end - start).days + 1
    pstart = start - timedelta(days=days)
    pend = start - timedelta(days=1)

    out = []
    for slug, prop in PROPERTIES.items():
        if property and slug != property:
            continue

        def stats(a: date, b: date, prop_slug: str) -> dict[str, Any]:
            row = conn.execute(
                "SELECT ROUND(AVG(rating),2), COUNT(*), "
                "SUM(sentiment='negative'), SUM(sentiment='positive') "
                "FROM reviews WHERE property_slug=? AND review_date>=? AND review_date<=?",
                (prop_slug, a.isoformat(), b.isoformat())).fetchone()
            avg, n, neg, pos = row
            return {"avg_rating": avg, "reviews": n or 0,
                    "negative": neg or 0, "positive": pos or 0}

        cur = stats(start, end, slug)
        prev = stats(pstart, pend, slug)
        top_issue = top_negative_topic(conn, slug, start, end)
        out.append({
            "slug": slug,
            "name": prop.name,
            "current": cur,
            "previous": prev,
            "delta_avg_rating": None if (cur["avg_rating"] is None or
                                         prev["avg_rating"] is None)
            else round(cur["avg_rating"] - prev["avg_rating"], 2),
            "top_issue_topic": top_issue,
        })
    return out


def top_negative_topic(conn: sqlite3.Connection, slug: str,
                       start: date, end: date) -> dict[str, Any] | None:
    """Most-complained-about topic for a property in range."""
    counts: dict[str, int] = {}
    for (topics_json,) in conn.execute(
            "SELECT topics_json FROM reviews WHERE property_slug=? "
            "AND review_date>=? AND review_date<=?",
            (slug, start.isoformat(), end.isoformat())):
        for t in json.loads(topics_json or "[]"):
            if t.get("polarity") in ("negative", "mixed"):
                counts[t["topic"]] = counts.get(t["topic"], 0) + 1
    if not counts:
        return None
    topic, n = max(counts.items(), key=lambda kv: (kv[1], kv[0]))
    return {"topic": topic, "mentions": n}


def trends(conn: sqlite3.Connection, property: str | None,
           start: date, end: date) -> list[dict[str, Any]]:
    """Weekly buckets: avg rating + sentiment mix per week (overall + per property)."""
    slugs = _clamp_filters([property] if property else None)
    ph = ",".join("?" * len(slugs))
    rows = conn.execute(
        f"SELECT {WEEK_START_SQL} AS week, property_slug, AVG(rating), "
        f"SUM(sentiment='positive'), SUM(sentiment='neutral'), "
        f"SUM(sentiment='negative'), COUNT(*) "
        f"FROM reviews WHERE property_slug IN ({ph}) "
        f"AND review_date>=? AND review_date<=? AND review_date IS NOT NULL "
        f"GROUP BY week, property_slug ORDER BY week",
        [*slugs, start.isoformat(), end.isoformat()]).fetchall()

    weeks: dict[str, dict] = {}
    for week, slug, avg, pos, neu, neg, n in rows:
        w = weeks.setdefault(week, {
            "week_start": week, "avg_rating": [], "reviews": 0,
            "positive": 0, "neutral": 0, "negative": 0,
            "by_property": {},
        })
        w["avg_rating"].append(avg)
        w["reviews"] += n
        w["positive"] += pos or 0
        w["neutral"] += neu or 0
        w["negative"] += neg or 0
        w["by_property"][slug] = {"avg_rating": round(avg, 2), "reviews": n}
    out = []
    for w in sorted(weeks.values(), key=lambda x: x["week_start"]):
        out.append({
            "week_start": w["week_start"],
            "avg_rating": round(sum(w["avg_rating"]) / len(w["avg_rating"]), 2),
            "reviews": w["reviews"],
            "positive": w["positive"],
            "neutral": w["neutral"],
            "negative": w["negative"],
            "by_property": w["by_property"],
        })
    return out


def topic_insights(conn: sqlite3.Connection, property: str | None,
                    start: date, end: date) -> list[dict[str, Any]]:
    """Topic breakdown of guest complaints, current period vs previous period.

    A review counts as a "complaint review" when its rating sentiment is
    negative OR its disliked section produced at least one negative/mixed
    topic mention (a rating-8 review that still gripe about noise is
    operationally relevant). pct = complaint reviews mentioning the topic.
    """
    slugs = _clamp_filters([property] if property else None)
    ph = ",".join("?" * len(slugs))
    days = (end - start).days + 1
    pstart, pend = start - timedelta(days=days), start - timedelta(days=1)

    def collect(a: date, b: date) -> tuple[dict[str, int], int]:
        counts: dict[str, int] = {}
        complaint_total = 0
        for sentiment, topics_json in conn.execute(
                f"SELECT sentiment, topics_json FROM reviews "
                f"WHERE property_slug IN ({ph}) AND review_date>=? "
                f"AND review_date<=?",
                [*slugs, a.isoformat(), b.isoformat()]):
            topics = json.loads(topics_json or "[]")
            bad = [t["topic"] for t in topics
                   if t.get("polarity") in ("negative", "mixed")]
            if bad or sentiment == "negative":
                complaint_total += 1
                for topic in set(bad):
                    counts[topic] = counts.get(topic, 0) + 1
        return counts, complaint_total

    cur_counts, cur_neg = collect(start, end)
    prev_counts, prev_neg = collect(pstart, pend)

    topics = set(cur_counts) | set(prev_counts)
    out = []
    for topic in topics:
        cur_n = cur_counts.get(topic, 0)
        cur_pct = round(100 * cur_n / cur_neg, 1) if cur_neg else None
        prev_pct = (round(100 * prev_counts.get(topic, 0) / prev_neg, 1)
                    if prev_neg else None)
        out.append({
            "topic": topic,
            "complaint_mentions": cur_n,
            "pct_of_complaints": cur_pct,
            "prev_pct_of_complaints": prev_pct,
            "delta_pp": None if (cur_pct is None or prev_pct is None)
            else round(cur_pct - prev_pct, 1),
        })
    out.sort(key=lambda t: (-(t["complaint_mentions"] or 0), t["topic"]))
    return {"topics": out, "complaint_reviews": cur_neg,
            "prev_complaint_reviews": prev_neg}


def query_reviews(conn: sqlite3.Connection, *, property: str | None,
                  start: date | None, end: date | None, topic: str | None,
                  sentiment: str | None, search: str | None,
                  sort: str, page: int, size: int) -> dict[str, Any]:
    """Review feed with filters. Topic filtering happens in Python (JSON)."""
    where, params = ["review_date IS NOT NULL"], []
    if property:
        where.append("property_slug = ?")
        params.append(property)
    if start:
        where.append("review_date >= ?")
        params.append(start.isoformat())
    if end:
        where.append("review_date <= ?")
        params.append(end.isoformat())
    if sentiment in ("positive", "neutral", "negative"):
        where.append("sentiment = ?")
        params.append(sentiment)
    if search:
        like = f"%{search.lower()}%"
        where.append("(LOWER(COALESCE(title,'')) LIKE ? OR "
                     "LOWER(COALESCE(positive_text,'')) LIKE ? OR "
                     "LOWER(COALESCE(negative_text,'')) LIKE ?)")
        params += [like, like, like]

    order = {
        "newest": "review_date DESC, id",
        "oldest": "review_date ASC, id",
        "worst": "rating ASC, review_date DESC",
        "best": "rating DESC, review_date DESC",
    }.get(sort, "review_date DESC, id")

    rows = [dict(r) for r in conn.execute(
        f"SELECT id, property_slug, reviewer_name, reviewer_country, rating, "
        f"title, positive_text, negative_text, review_date, stay_period, nights, "
        f"room_type, traveler_type, hotel_response, sentiment, topics_json, "
        f"classified_by FROM reviews WHERE {' AND '.join(where)} ORDER BY {order}",
        params)]

    matched = rows
    if topic:
        matched = [r for r in rows if any(
            t["topic"] == topic for t in json.loads(r["topics_json"] or "[]"))]

    total = len(matched)
    size = max(1, min(size, 100))
    page = max(1, page)
    window = matched[(page - 1) * size: page * size]
    for r in window:
        r["topics"] = json.loads(r.pop("topics_json") or "[]")
    return {"total": total, "page": page, "size": size,
            "pages": (total + size - 1) // size, "reviews": window}


def meta(conn: sqlite3.Connection) -> dict[str, Any]:
    from ..config import PROPERTIES
    row = conn.execute(
        "SELECT COUNT(*), MIN(review_date), MAX(review_date) FROM reviews"
    ).fetchone()
    last_run = conn.execute(
        "SELECT mode, status, started_at, finished_at, reviews_new "
        "FROM scrape_runs ORDER BY id DESC LIMIT 1").fetchone()
    per_property = [dict(r) for r in conn.execute(
        "SELECT property_slug AS slug, COUNT(*) AS reviews, "
        "ROUND(AVG(rating),2) AS avg_rating FROM reviews GROUP BY property_slug")]
    classification = {
        (row[0] or "unclassified"): row[1]
        for row in conn.execute(
            "SELECT classified_by, COUNT(*) FROM reviews GROUP BY classified_by")
    }
    names = {s: p.name for s, p in PROPERTIES.items()}
    for pp in per_property:
        pp["name"] = names.get(pp["slug"], pp["slug"])
    return {
        "total_reviews": row[0],
        "date_range": {"start": row[1], "end": row[2]},
        "last_scrape_run": dict(last_run) if last_run else None,
        "per_property": per_property,
        "classification": classification,
        "properties": [{"slug": s, "name": p.name} for s, p in PROPERTIES.items()],
    }
