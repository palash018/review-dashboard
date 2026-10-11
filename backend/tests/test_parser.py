from azzurro.database import review_id
from azzurro.scraper.parser import (
    parse_nights,
    parse_rating,
    parse_review_date,
    parse_stay_period,
)


def test_parse_review_date():
    assert parse_review_date("Reviewed: 3 October 2026") == "2026-10-03"
    assert parse_review_date("Reviewed: 21 December 2025") == "2025-12-21"
    assert parse_review_date("garbage") is None
    assert parse_review_date("") is None


def test_parse_stay_period():
    assert parse_stay_period("September 2026") == "2026-09"
    assert parse_stay_period("2 nights\xa0·\xa0January 2025") == "2025-01"
    assert parse_stay_period("2 nights") is None


def test_parse_nights():
    assert parse_nights("1 night\xa0·\xa0") == 1
    assert parse_nights("3 nights") == 3
    assert parse_nights("September 2026") is None


def test_parse_rating():
    assert parse_rating("Scored 7.0\n8.0") == 7.0
    assert parse_rating("Scored 10\n10") == 10.0
    assert parse_rating("") is None


def test_review_id_stable_and_sensitive():
    a = review_id("x", "Ann", "2026-01-01", 8.0, "T", "text")
    b = review_id("x", "Ann", "2026-01-01", 8.0, "T", "text")
    c = review_id("x", "ann", "2026-01-01", 8.0, "t", "Text")
    d = review_id("x", "Ann", "2026-01-01", 9.0, "T", "text")
    assert a == b
    assert a == c      # case-insensitive normalisation
    assert a != d      # rating difference -> different review
