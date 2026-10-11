"""API tests over a fixture DB (no network, no browser)."""
import pathlib
import tempfile
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from azzurro import config
from azzurro.classification.keyword import classify_record
from azzurro.database import connect, init_db, review_id, utc_now_iso


@pytest.fixture()
def client(monkeypatch):
    tmp = tempfile.mkdtemp()
    db = pathlib.Path(tmp) / "test.db"
    monkeypatch.setattr(config, "DB_PATH", db)
    conn = connect(db)
    init_db(conn)

    today = date(2026, 10, 11)          # a Sunday
    cols = ("id property_slug reviewer_name reviewer_country rating title "
            "positive_text negative_text review_date stay_period nights "
            "room_type traveler_type hotel_response sentiment topics_json "
            "classified_by first_seen_at collected_at").split()
    for i, spec in enumerate([
        # (days ago, slug, rating, pos, neg)
        (2, "olympic-paddington", 9.0, "Great location and friendly staff", None),
        (3, "olympic-paddington", 4.0, "ok", "Dirty bathroom and rude staff"),
        (4, "potts-point", 8.0, "Clean room", "Thin walls, very noisy"),
        (5, "potts-point", 7.5, "Good value", None),
        (9, "central-sydney", 3.0, None, "Filthy room, not worth the money"),
        (10, "central-sydney", 10.0, "Perfect, spotless", None),
        (12, "darling-harbour", 6.0, "Fine", "Slow check in"),
    ]):
        d = today - timedelta(days=spec[0])
        rec = {
            "property_slug": spec[1],
            "reviewer_name": f"Guest{i}",
            "reviewer_country": "Australia",
            "rating": spec[2],
            "title": "Title",
            "positive_text": spec[3],
            "negative_text": spec[4],
            "review_date": d.isoformat(),
            "stay_period": d.strftime("%Y-%m"),
            "nights": 2,
            "room_type": "Double",
            "traveler_type": "Couple",
            "hotel_response": None,
        }
        rec["id"] = review_id(spec[1], rec["reviewer_name"], rec["review_date"],
                              spec[2], "Title", spec[3] or spec[4] or "")
        classify_record(rec)
        rec["first_seen_at"] = rec["collected_at"] = utc_now_iso()
        placeholders = ", ".join("?" * len(cols))
        conn.execute(
            f"INSERT INTO reviews ({', '.join(cols)}) VALUES ({placeholders})",
            [rec[c] for c in cols],
        )
    conn.commit()

    from azzurro.api.main import app
    with TestClient(app) as c:
        yield c
    conn.close()


def test_meta(client):
    r = client.get("/api/meta")
    assert r.status_code == 200
    body = r.json()
    assert body["total_reviews"] == 7
    assert len(body["properties"]) == 4


def test_meta_classification_counts(client):
    body = client.get("/api/meta").json()
    assert body["classification"]["keyword"] == 7
    assert body["classification"].get("llm", 0) == 0


def test_kpis_current_vs_prev_week(client):
    r = client.get("/api/kpis", params={"start": "2026-10-05", "end": "2026-10-11"})
    body = r.json()
    assert r.status_code == 200
    # week Mon 2026-10-05 .. Sun 2026-10-11 contains 4 reviews
    assert body["period"] == {"start": "2026-10-05", "end": "2026-10-11", "days": 7}
    assert body["prev_period"]["end"] == "2026-10-04"
    assert body["current"]["reviews"] == 4
    assert body["previous"]["reviews"] == 3  # prev week has 3 (9,10,12 days ago)
    assert body["previous"]["has_data"] is True
    assert body["delta"]["reviews"] == 1
    assert body["current"]["avg_rating"] is not None


def test_kpis_multiweek_range_all_time_style(client):
    """Long ranges summarise the WHOLE period, not just the final week."""
    r = client.get("/api/kpis", params={"start": "2026-09-28", "end": "2026-10-11"})
    body = r.json()
    assert body["period"]["days"] == 14
    assert body["current"]["reviews"] == 7  # every fixture review
    assert body["previous"]["reviews"] == 0
    assert body["previous"]["has_data"] is False
    assert body["delta"]["reviews"] is None      # nothing before data start
    assert body["delta"]["avg_rating"] is None


def test_kpis_single_property(client):
    r = client.get("/api/kpis", params={"start": "2026-10-05", "end": "2026-10-11",
                                        "property": "potts-point"})
    body = r.json()
    assert body["current"]["reviews"] == 2


def test_property_breakdown(client):
    r = client.get("/api/properties/breakdown",
                   params={"start": "2026-10-05", "end": "2026-10-11"})
    body = r.json()
    assert len(body) == 4
    olympic = next(p for p in body if p["slug"] == "olympic-paddington")
    assert olympic["current"]["reviews"] == 2
    assert olympic["top_issue_topic"]["topic"] in ("cleanliness", "staff")


def test_insights_percentages(client):
    r = client.get("/api/insights",
                   params={"start": "2026-10-05", "end": "2026-10-11"})
    body = r.json()
    assert body["complaint_reviews"] == 2
    topics = {t["topic"]: t for t in body["topics"]}
    # complaint reviews in week: olympic 4.0 (dirty, rude), potts 8.0 (noisy)
    assert topics["cleanliness"]["complaint_mentions"] == 1
    assert topics["cleanliness"]["pct_of_complaints"] == 50.0
    assert topics["noise"]["complaint_mentions"] == 1
    assert topics["noise"]["pct_of_complaints"] == 50.0


def test_reviews_filters(client):
    r = client.get("/api/reviews", params={"topic": "noise"})
    body = r.json()
    assert body["total"] == 1
    assert body["reviews"][0]["property_slug"] == "potts-point"

    r = client.get("/api/reviews", params={"sentiment": "negative"})
    assert r.json()["total"] >= 2

    r = client.get("/api/reviews", params={"search": "spotless"})
    assert r.json()["total"] == 1

    r = client.get("/api/reviews",
                   params={"start": "2026-09-29", "end": "2026-10-04"})
    assert r.json()["total"] == 3  # 9, 10 and 12 days ago (Sep 29 in range)

    r = client.get("/api/reviews", params={"sort": "worst", "size": 3})
    reviews = r.json()["reviews"]
    ratings = [x["rating"] for x in reviews]
    assert ratings == sorted(ratings)


def test_reviews_pagination(client):
    r = client.get("/api/reviews", params={"size": 3, "page": 2})
    body = r.json()
    assert body["total"] == 7
    assert body["pages"] == 3
    assert len(body["reviews"]) == 3


def test_trends_weekly_buckets(client):
    r = client.get("/api/trends",
                   params={"start": "2026-09-28", "end": "2026-10-11"})
    weeks = r.json()
    assert weeks, "expected at least one week bucket"
    assert all(w["week_start"] for w in weeks)
    this_week = next(w for w in weeks if w["week_start"] == "2026-10-05")
    assert this_week["reviews"] == 4
    assert this_week["negative"] >= 1


def test_invalid_date_400(client):
    r = client.get("/api/kpis", params={"start": "not-a-date"})
    assert r.status_code == 400
