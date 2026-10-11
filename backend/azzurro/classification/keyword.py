"""Deterministic keyword classifier (always available, no API keys).

Methodology
-----------
* Topics: 8 operational lexicons (see lexicons.py).
* Polarity per topic: Booking.com splits every review into a "Liked"
  (positive_text) and "Disliked" (negative_text) section. A lexicon hit in
  the negative section = negative mention of that topic, and vice versa.
  Both sides hit equally -> mixed.
* Review sentiment: anchored on the numeric rating (>=8 positive, <=6
  negative, else neutral). Text signals refine the borderline band
  (rating 7 with no negative text -> positive lean recorded as-is).

Limitations (documented in README):
* keyword recall is imperfect (synonyms, sarcasm, typos);
* a review can mention many topics - we report all hits, not a single label.
"""
from __future__ import annotations

import json
import re
from typing import Any

from .. import config
from .lexicons import NEGATIONS, TOPICS


def _compile(topic_words: list[str]) -> list[tuple[str, re.Pattern]]:
    out = []
    for w in topic_words:
        # longer phrases first is handled by sorting at match time
        pattern = re.compile(r"\b" + re.escape(w) + r"\b", re.IGNORECASE)
        out.append((w, pattern))
    return out


_COMPILED = {topic: _compile(words) for topic, words in TOPICS.items()}


def _find_hits(text: str, compiled: list[tuple[str, re.Pattern]]) -> list[str]:
    return [w for w, pat in compiled if pat.search(text)]


def _has_negation(text: str) -> bool:
    low = text.lower()
    return any(re.search(r"\b" + re.escape(n) + r"\b", low) for n in NEGATIONS)


def sentiment_from_rating(rating: float | None,
                          positive_text: str, negative_text: str) -> str:
    if rating is None:
        # fall back to text presence
        if negative_text and not positive_text:
            return "negative"
        if positive_text and not negative_text:
            return "positive"
        return "neutral"
    if rating >= config.RATING_POSITIVE_MIN:
        return "positive"
    if rating <= config.RATING_NEGATIVE_MAX:
        return "negative"
    # borderline 6.x-7.9: long, substantive complaints drag it to negative
    heavy_complaint = (
        len(negative_text) > 300
        and len(negative_text) > 3 * max(len(positive_text), 1)
    )
    if negative_text and heavy_complaint:
        return "negative"
    return "neutral"


def classify_record(record: dict[str, Any]) -> dict[str, Any]:
    """Attach sentiment + topics to a raw scraped record (in place)."""
    positive = record.get("positive_text") or ""
    negative = record.get("negative_text") or ""
    topics: list[dict[str, Any]] = []

    for topic, compiled in _COMPILED.items():
        pos_hits = _find_hits(positive, compiled)
        neg_hits = _find_hits(negative, compiled)
        if not pos_hits and not neg_hits:
            continue
        if neg_hits and not pos_hits:
            polarity = "negative"
        elif pos_hits and not neg_hits:
            polarity = "positive"
        else:
            polarity = "mixed"
        # Negation guard: "not clean" inside the positive section is not a
        # positive cleanliness mention.
        if pos_hits and _has_negation(positive):
            polarity = "mixed"
        topics.append({
            "topic": topic,
            "polarity": polarity,
            "keywords": sorted(set(pos_hits + neg_hits)),
        })

    # Most negative topics first (stable for the UI)
    order = {"negative": 0, "mixed": 1, "positive": 2}
    topics.sort(key=lambda t: (order[t["polarity"]], t["topic"]))

    record["sentiment"] = sentiment_from_rating(
        record.get("rating"), positive, negative)
    record["topics_json"] = json.dumps(topics)
    record["classified_by"] = "keyword"
    return record
