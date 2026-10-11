"""DB-level idempotency: the same review can never be counted twice."""
import pathlib

from azzurro.database import connect, init_db, review_id, upsert_review


def _record(i: int = 1, rating: float = 8.0):
    rec = {
        "id": review_id("olympic-paddington", "Ann", "2026-10-05", rating,
                        "Great stay", "loved the location and staff"),
        "property_slug": "olympic-paddington",
        "reviewer_name": "Ann", "reviewer_country": "Australia",
        "rating": rating, "title": "Great stay",
        "positive_text": "loved the location and staff",
        "negative_text": None, "review_date": "2026-10-05",
        "stay_period": "2026-10", "nights": 2, "room_type": "Double",
        "traveler_type": "Couple", "hotel_response": None,
        "sentiment": "positive", "topics_json": "[]",
        "classified_by": "keyword",
        "first_seen_at": "2026-10-11T00:00:00Z",
        "collected_at": "2026-10-11T00:00:00Z",
    }
    return rec


def test_double_upsert_is_noop(tmp_path: pathlib.Path):
    db = tmp_path / "t.db"
    conn = connect(db)
    init_db(conn)
    rec = _record()
    assert upsert_review(conn, rec) is True       # first insert: new
    assert upsert_review(conn, rec) is False      # exact same review again
    assert upsert_review(conn, dict(rec)) is False  # fresh dict, same content
    assert conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1


def test_case_and_whitespace_variants_dedupe(tmp_path: pathlib.Path):
    conn = connect(tmp_path / "t2.db")
    init_db(conn)
    upsert_review(conn, _record())
    variant = _record()
    variant["id"] = review_id(
        "olympic-paddington", " ann ", "2026-10-05", 8.0,
        "  GREAT STAY ", "Loved the Location and Staff  ")
    assert upsert_review(conn, variant) is False  # normalised -> same review
    assert conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 1


def test_different_content_is_a_new_review(tmp_path: pathlib.Path):
    conn = connect(tmp_path / "t3.db")
    init_db(conn)
    upsert_review(conn, _record(rating=8.0))
    other = _record(rating=5.0)  # different rating -> genuinely different review
    assert upsert_review(conn, other) is True
    assert conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 2


def test_reviewer_same_day_two_stays(tmp_path: pathlib.Path):
    """Same reviewer, same rating, same day but different text = different
    review (hash includes text prefix, not just identity)."""
    conn = connect(tmp_path / "t4.db")
    init_db(conn)
    upsert_review(conn, _record())
    other = _record()
    other["positive_text"] = "spotless room, quiet street"
    other["id"] = review_id("olympic-paddington", "Ann", "2026-10-05", 8.0,
                            "Great stay", other["positive_text"])
    assert upsert_review(conn, other) is True
    assert conn.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 2
