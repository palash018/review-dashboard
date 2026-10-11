"""Parse a Playwright review-card ElementHandle into a plain record dict."""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from .selectors import SELECTORS

log = logging.getLogger(__name__)

_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}


def _text(loc) -> str:
    """Inner text of a locator, or '' when absent (count() avoids the timeout)."""
    try:
        if loc.count() == 0:
            return ""
        return (loc.first.inner_text(timeout=3000) or "").strip()
    except Exception:
        return ""


def _clean_label(text: str, prefixes: tuple[str, ...]) -> str:
    for p in prefixes:
        if text.lower().startswith(p.lower()):
            text = text[len(p):]
            break
    return text.strip()


def parse_review_date(raw: str) -> str | None:
    """'Reviewed: 3 October 2026' -> '2026-10-03'."""
    m = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw)
    if not m:
        return None
    day, month, year = m.groups()
    mon = _MONTHS.get(month.lower())
    if not mon:
        return None
    try:
        return datetime(int(year), mon, int(day)).strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_stay_period(raw: str) -> str | None:
    """'September 2026' (or '2 nights · September 2026') -> '2026-09'."""
    m = re.search(r"([A-Za-z]+)\s+(\d{4})", raw)
    if not m:
        return None
    month, year = m.groups()
    mon = _MONTHS.get(month.lower())
    if not mon:
        return None
    return f"{int(year):04d}-{mon:02d}"


def parse_nights(raw: str) -> int | None:
    m = re.search(r"(\d+)\s+nights?", raw)
    return int(m.group(1)) if m else None


def parse_rating(raw: str) -> float | None:
    m = re.search(r"(\d{1,2}(?:\.\d)?)", raw)
    return float(m.group(1)) if m else None


def parse_card(card, slug: str) -> dict[str, Any] | None:
    """Extract one review record. Returns None when the card is unusable."""
    try:
        title = _clean_label(_text(card.locator(SELECTORS["title"])),
                             ("Reviewed:",))
        score_raw = _text(card.locator(SELECTORS["score"]))
        rating = parse_rating(score_raw)
        date_raw = _text(card.locator(SELECTORS["review_date"]))
        review_date = parse_review_date(date_raw)
        nights_stay = _text(card.locator(SELECTORS["nights_and_stay"]))
        stay_date_raw = _text(card.locator(SELECTORS["stay_date"])) or nights_stay

        reviewer = _text(card.locator(SELECTORS["reviewer_name"]))
        try:
            country_img = card.locator(SELECTORS["reviewer_country_img"])
            country = (country_img.first.get_attribute("alt", timeout=3000)
                       if country_img.count() else "") or ""
        except Exception:
            country = ""

        positive = _clean_label(
            _text(card.locator(SELECTORS["positive_text"])), ("Liked:",))
        negative = _clean_label(
            _text(card.locator(SELECTORS["negative_text"])), ("Disliked:",))

        reply = _clean_label(_text(card.locator(SELECTORS["partner_reply"])),
                             ("Hotel response:",))
        reply = re.sub(r"\s*Continue reading\s*$", "", reply).strip()

        record: dict[str, Any] = {
            "property_slug": slug,
            "reviewer_name": reviewer or None,
            "reviewer_country": country.strip() or None,
            "rating": rating,
            "title": title or None,
            "positive_text": positive or None,
            "negative_text": negative or None,
            "review_date": review_date,
            "stay_period": parse_stay_period(stay_date_raw),
            "nights": parse_nights(nights_stay),
            "room_type": _text(card.locator(SELECTORS["room_name"])) or None,
            "traveler_type": _clean_label(
                _text(card.locator(SELECTORS["traveler_type"])), ("Reviewed:",)) or None,
            "hotel_response": reply or None,
        }
        # Unusable card guard: need at least a rating or some text
        if record["rating"] is None and not (positive or negative):
            log.warning("Skipping unusable card for %s (no rating, no text)", slug)
            return None
        return record
    except Exception as exc:  # never let one bad card kill a run
        log.warning("Failed to parse a review card for %s: %s", slug, exc)
        return None
