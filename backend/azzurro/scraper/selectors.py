"""All Booking.com DOM selectors in ONE place.

If Booking.com changes their markup, this file is the only thing that needs
updating (see parser.py for how each selector is used).
"""
from __future__ import annotations

SELECTORS = {
    # Header nav tab that opens the reviews section
    "reviews_tab": '[data-testid="Property-Header-Nav-Tab-Trigger-reviews"]',
    # <select> controlling review sort order
    "sorter": 'select#reviewListSorters',
    # Container holding the current page of review cards
    "cards": '[data-testid="review-cards"] [data-testid="review-card"]',
    # Per-card fields
    "avatar": '[data-testid="review-avatar"]',
    "reviewer_name": '[data-testid="review-avatar"] h4',
    "reviewer_country_img": '[data-testid="review-avatar"] img[alt]:not([alt=""])',
    "room_name": '[data-testid="review-room-name"]',
    "nights_and_stay": '[data-testid="review-num-nights"]',
    "stay_date": '[data-testid="review-stay-date"]',
    "traveler_type": '[data-testid="review-traveler-type"]',
    "review_date": '[data-testid="review-date"]',
    "title": '[data-testid="review-title"]',
    "score": '[data-testid="review-score"]',
    "positive_text": '[data-testid="review-positive-text"]',
    "negative_text": '[data-testid="review-negative-text"]',
    "partner_reply": '[data-testid="review-partner-reply"]',
    # Pagination
    "next_page": 'button[aria-label="Next page"]',
}

SORT_NEWEST_FIRST = "NEWEST_FIRST"
