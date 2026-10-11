"""Collection orchestration: navigate hotel pages, paginate reviews, dedup."""
from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from typing import Any

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PWTimeoutError

from .. import config
from ..database import review_id
from .browser import BotChallengeError, check_for_challenge, dismiss_consent
from .parser import parse_card
from .selectors import SELECTORS, SORT_NEWEST_FIRST

log = logging.getLogger(__name__)

_FAST_MODE = False  # set by run_scraper(); trims polite delays for quick refreshes

# Rough per-property WORK estimates (seconds, excl. inter-property gaps) for ETA.
_ETA_PER_PROPERTY = {"update": {"normal": 12, "fast": 12},
                     "backfill": {"normal": 240, "fast": 150}}

RecordSink = Callable[[list[dict[str, Any]]], int]
"""Sink receives freshly parsed records, returns how many were NEW."""


def _polite(kind: str) -> None:
    """Sleep a jittered polite delay ('page' or 'property')."""
    ranges = {
        ("page", False): config.PAGE_DELAY_RANGE_S,
        ("property", False): config.PROPERTY_DELAY_RANGE_S,
        ("page", True): config.FAST_PAGE_DELAY_RANGE_S,
        ("property", True): config.FAST_PROPERTY_DELAY_RANGE_S,
    }
    time.sleep(random.uniform(*ranges[(kind, _FAST_MODE)]))


def open_reviews_tab(page: Page, url: str) -> None:
    page.goto(url, wait_until="domcontentloaded", timeout=config.NAV_TIMEOUT_MS)
    page.wait_for_timeout(3000)
    dismiss_consent(page)
    check_for_challenge(page)
    page.locator(SELECTORS["reviews_tab"]).first.click(timeout=10000)
    page.wait_for_selector(SELECTORS["cards"], timeout=config.CARD_WAIT_TIMEOUT_MS)


def sort_newest_first(page: Page) -> None:
    try:
        page.locator(SELECTORS["sorter"]).select_option(SORT_NEWEST_FIRST)
        page.wait_for_timeout(2000)  # allow card list refresh
        page.wait_for_selector(SELECTORS["cards"], timeout=config.CARD_WAIT_TIMEOUT_MS)
    except Exception as exc:
        log.warning("Could not switch sorter to newest-first (%s); using default", exc)


def _click_next(page: Page) -> bool:
    """Click 'Next page'. Returns False when on the last page."""
    btn = page.locator(SELECTORS["next_page"]).first
    try:
        if btn.get_attribute("disabled", timeout=5000) is not None:
            return False
    except PWTimeoutError:
        return False
    except Exception:
        pass  # attribute absent -> not disabled
    btn.click(timeout=10000)
    page.wait_for_timeout(1800)
    page.wait_for_selector(SELECTORS["cards"], timeout=config.CARD_WAIT_TIMEOUT_MS)
    check_for_challenge(page)
    return True


def parse_current_page(page: Page, slug: str) -> list[dict[str, Any]]:
    cards = page.locator(SELECTORS["cards"]).all()
    return [r for r in (parse_card(c, slug) for c in cards) if r]


def with_stable_ids(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def combined(r: dict[str, Any]) -> str:
        return " ".join(filter(None, [r.get("positive_text"), r.get("negative_text")]))
    for r in records:
        r["id"] = review_id(
            r["property_slug"], r.get("reviewer_name") or "",
            r.get("review_date") or "", r.get("rating"),
            r.get("title") or "", combined(r))
    return records


def collect_property(page: Page, slug: str, mode: str,
                     sink: RecordSink) -> dict[str, Any]:
    """Scrape one property.

    mode 'backfill': paginate up to BACKFILL_TARGET_PER_PROPERTY new reviews.
    mode 'update':   stop at the first page that yields no new reviews
                     (reviews are sorted newest-first).
    """
    from ..config import PROPERTIES  # local import to keep module import light

    prop = PROPERTIES[slug]
    url = config.HOTEL_URL_TEMPLATE.format(url_slug=prop.url_slug)
    result: dict[str, Any] = {"slug": slug, "seen": 0, "new": 0, "pages": 0,
                              "error": None}
    target = config.BACKFILL_TARGET_PER_PROPERTY if mode == "backfill" else 10**9

    open_reviews_tab(page, url)
    sort_newest_first(page)

    run_ids: set[str] = set()
    while True:
        records = with_stable_ids(parse_current_page(page, slug))
        fresh = [r for r in records if r["id"] not in run_ids]
        for r in fresh:
            run_ids.add(r["id"])
        result["seen"] += len(fresh)
        new_count = sink(fresh) if fresh else 0
        result["new"] += new_count
        result["pages"] += 1
        log.info("[%s] page %d: %d parsed, %d new (total new %d)",
                 slug, result["pages"], len(fresh), new_count, result["new"])

        if mode == "update" and new_count == 0:
            break  # reached previously-seen territory (newest-first sort)
        if result["new"] >= target:
            break
        if result["pages"] >= config.MAX_PAGES_PER_PROPERTY:
            log.warning("[%s] hit MAX_PAGES cap (%d)", slug, config.MAX_PAGES_PER_PROPERTY)
            break

        _polite("page")
        clicked = False
        for attempt in range(1, config.PAGE_ACTION_RETRIES + 1):
            try:
                clicked = _click_next(page)
                break
            except BotChallengeError:
                raise
            except Exception as exc:
                log.warning("[%s] pagination attempt %d failed: %s", slug, attempt, exc)
                time.sleep(2 * attempt)
        if not clicked:
            log.info("[%s] no next page - finished after %d pages", slug, result["pages"])
            break
    return result


def run_scraper(conn, mode: str, slugs: list[str] | None = None,
                classify_fn=None, fast: bool = False) -> dict[str, Any]:
    """Top-level entry: scrape the given (or all) properties, log a run."""
    from .. import config
    from ..database import (
        finish_run,
        known_review_ids,
        start_run,
        upsert_review,
        utc_now_iso,
    )

    slugs = slugs or list(config.PROPERTIES)
    classify_fn = classify_fn or (lambda r: r)
    known = known_review_ids(conn)
    run_id = start_run(conn, mode)
    results: list[dict[str, Any]] = []
    status = "completed"

    global _FAST_MODE
    _FAST_MODE = bool(fast)

    # ETA banner: rough wall-clock estimate so the operator knows what to expect
    per_prop = _ETA_PER_PROPERTY[mode]["fast" if _FAST_MODE else "normal"]
    gap = (config.FAST_PROPERTY_DELAY_RANGE_S[1] if _FAST_MODE
           else config.PROPERTY_DELAY_RANGE_S[1])
    est_total = len(slugs) * per_prop + (len(slugs) - 1) * gap
    speed_note = " (fast pacing)" if _FAST_MODE else ""
    print(f"→ {mode} for {len(slugs)} propert{'y' if len(slugs) == 1 else 'ies'}"
          f"{speed_note}: estimated {est_total // 60}–{round(est_total * 1.3) // 60} min"
          f" (polite pacing keeps us under Booking.com's bot radar)", flush=True)

    from .browser import launch_browser, new_context
    pw, browser = launch_browser()
    run_started = time.monotonic()
    try:
        context = new_context(browser)
        page = context.new_page()
        for idx, slug in enumerate(slugs):
            if idx:
                _polite("property")
            prop_started = time.monotonic()
            print(f"[{idx + 1}/{len(slugs)}] {slug}: opening page…", flush=True)
            prop_result: dict[str, Any] | None = None
            for attempt in range(1, config.PROPERTY_ATTEMPTS + 1):
                try:
                    def sink(records, _known=known):
                        added = 0
                        for rec in records:
                            rec = classify_fn(rec)
                            rec["first_seen_at"] = utc_now_iso()
                            rec["collected_at"] = utc_now_iso()
                            if upsert_review(conn, rec):
                                known.add(rec["id"])
                                added += 1
                        conn.commit()  # incremental commit: partial data survives crashes
                        return added

                    prop_result = collect_property(page, slug, mode, sink)
                    break
                except BotChallengeError as exc:
                    wait = config.CHALLENGE_COOLDOWN_S * attempt
                    log.warning("[%s] bot challenge (attempt %d/%d): %s - cooling down %.0fs",
                                slug, attempt, config.PROPERTY_ATTEMPTS, exc, wait)
                    time.sleep(wait)
                    try:
                        page.close()
                        page = context.new_page()
                    except Exception:
                        context = new_context(browser)
                        page = context.new_page()
                except Exception as exc:
                    log.exception("[%s] scrape failed (attempt %d/%d): %s",
                                  slug, attempt, config.PROPERTY_ATTEMPTS, exc)
                    time.sleep(10 * attempt)
                    try:
                        page.close()
                        page = context.new_page()
                    except Exception:
                        context = new_context(browser)
                        page = context.new_page()
            if prop_result is None:
                prop_result = {"slug": slug, "seen": 0, "new": 0, "pages": 0,
                               "error": "failed after all attempts"}
                status = "partial"
            elif prop_result.get("error"):
                status = "partial"
            results.append(prop_result)
            conn.commit()  # ensure run-so-far durability

            # Progress line with ETA for the remaining properties
            took = time.monotonic() - prop_started
            remaining = len(slugs) - idx - 1
            eta_left = remaining * (took + (config.FAST_PROPERTY_DELAY_RANGE_S[1]
                               if _FAST_MODE else config.PROPERTY_DELAY_RANGE_S[1]))
            prop = config.PROPERTIES[slug]
            err = f" ⚠ {prop_result['error']}" if prop_result.get("error") else ""
            tail = (f" · ~{eta_left // 60} min {eta_left % 60:.0f}s remaining"
                    if remaining else " · done")
            print(f"[{idx + 1}/{len(slugs)}] {prop.name}: {prop_result['new']} new, "
                  f"{prop_result['seen']} checked in {took:.0f}s"
                  f"{' — up to date' if prop_result['new'] == 0 else ''}{err}{tail}",
                  flush=True)
    except Exception as exc:
        log.exception("Scraper run crashed: %s", exc)
        status = "failed"
        raise
    finally:
        browser.close()
        pw.stop()
        seen = sum(r.get("seen", 0) for r in results)
        new = sum(r.get("new", 0) for r in results)
        finish_run(conn, run_id, status, results, seen, new)
    print(f"✓ {mode} finished in {(time.monotonic() - run_started) / 60:.1f} min: "
          f"{new} new reviews, status {status}", flush=True)
    return {"run_id": run_id, "status": status, "results": results}
