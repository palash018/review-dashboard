"""Central configuration: properties, paths, politeness limits, thresholds."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "reviews.db"
EXPORT_PATH = DATA_DIR / "reviews_export.json"

# ---------------------------------------------------------------------------
# Properties (public Booking.com pages only - robots.txt allows /hotel/* for
# generic agents; we never touch internal JSON/fragment endpoints).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Property:
    slug: str          # internal key + Booking.com URL slug
    name: str          # business-facing name used across the dashboard
    url_slug: str      # Booking.com path segment after /hotel/au/


PROPERTIES: dict[str, Property] = {
    p.slug: p
    for p in [
        Property("olympic-paddington", "Olympic Hotel Paddington", "olympic-paddington"),
        Property("potts-point", "Potts Point", "venus-potts-point-sydney"),
        Property("central-sydney", "Central Sydney", "venus-surry-hills"),
        Property("darling-harbour", "Darling Harbour", "chateau-de-venus"),
    ]
}

HOTEL_URL_TEMPLATE = "https://www.booking.com/hotel/au/{url_slug}.en-gb.html"

# ---------------------------------------------------------------------------
# Scraping behaviour
# ---------------------------------------------------------------------------

BACKFILL_TARGET_PER_PROPERTY = 200   # cap; fewer if the property has fewer reviews
MAX_PAGES_PER_PROPERTY = 40          # hard safety cap (10 reviews per page)
PAGE_DELAY_RANGE_S = (2.5, 6.0)      # polite delay between pagination clicks
PROPERTY_DELAY_RANGE_S = (10.0, 25.0)
# Faster pacing for --fast runs: still polite, but trimmed for daily refreshes
FAST_PAGE_DELAY_RANGE_S = (1.0, 2.0)
FAST_PROPERTY_DELAY_RANGE_S = (3.0, 6.0)
PAGE_ACTION_RETRIES = 3              # retries for a single pagination click
PROPERTY_ATTEMPTS = 3                # whole-property retries (challenge/network)
CHALLENGE_COOLDOWN_S = 45.0          # backoff when a bot challenge is detected
NAV_TIMEOUT_MS = 60_000
CARD_WAIT_TIMEOUT_MS = 15_000

# Markers that indicate we hit a bot-check / block interstitial instead of the
# hotel page. Checked against page title and body text.
CHALLENGE_MARKERS = [
    "press & hold",
    "press and hold",
    "pardon our interruption",
    "access denied",
    "are you a human",
    "unusual traffic",
    "captcha",
]

# Consent / dismiss banners that may appear before we can interact.
CONSENT_SELECTORS = [
    "button#onetrust-accept-btn-handler",
    "button[aria-label='Dismiss sign-in info.']",
    "[aria-label='Dismiss sign in information.']",
]

# ---------------------------------------------------------------------------
# Classification thresholds (Booking.com 1-10 scale)
# ---------------------------------------------------------------------------

RATING_POSITIVE_MIN = 8.0   # rating >= 8  -> positive
RATING_NEGATIVE_MAX = 6.0   # rating <= 6  -> negative; between -> neutral
