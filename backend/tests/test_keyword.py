from azzurro.classification.keyword import classify_record, sentiment_from_rating
from azzurro.classification.lexicons import TOPICS


def _rec(positive=None, negative=None, rating=None):
    return {"positive_text": positive, "negative_text": negative, "rating": rating}


def test_topics_cover_required_categories():
    required = {"cleanliness", "check-in", "staff", "noise", "facilities",
                "location", "room-condition", "value"}
    assert required <= set(TOPICS)


def test_section_polarity():
    rec = classify_record(_rec(positive="Great location",
                               negative="Dirty bathroom", rating=6.0))
    topics = {t["topic"]: t["polarity"] for t in rec["topics_json"]
              } if isinstance(rec["topics_json"], list) else None
    import json
    topics = {t["topic"]: t["polarity"]
              for t in json.loads(rec["topics_json"])}
    assert topics["location"] == "positive"
    assert topics["cleanliness"] == "negative"
    assert rec["sentiment"] == "negative"


def test_negation_in_positive_section_downgrades_to_mixed():
    import json
    rec = classify_record(_rec(positive="Room was not clean at all",
                               rating=7.0))
    topics = {t["topic"]: t["polarity"]
              for t in json.loads(rec["topics_json"])}
    assert topics.get("cleanliness") in ("mixed", "negative")


def test_no_topics_when_no_hits():
    rec = classify_record(_rec(positive="Fine", rating=8.5))
    import json
    assert json.loads(rec["topics_json"]) == []
    assert rec["sentiment"] == "positive"


def test_sentiment_thresholds():
    assert sentiment_from_rating(9.0, "", "") == "positive"
    assert sentiment_from_rating(4.5, "x", "y") == "negative"
    assert sentiment_from_rating(7.0, "ok", "") == "neutral"
    assert sentiment_from_rating(None, "", "bad stuff") == "negative"
    assert sentiment_from_rating(None, "", "") == "neutral"


def test_borderline_rating_dragged_negative_by_long_complaint():
    long_neg = "The room was dirty and noisy. " * 15
    assert sentiment_from_rating(7.0, "fine", long_neg) == "negative"
    assert sentiment_from_rating(7.0, "fine", "bit small") == "neutral"
