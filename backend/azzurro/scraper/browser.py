"""Browser lifecycle, bot-challenge detection, consent banner handling."""
from __future__ import annotations

import logging

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

from .. import config

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


class BotChallengeError(RuntimeError):
    """Raised when Booking.com serves a bot-check interstitial."""


def launch_browser() -> tuple[object, Browser]:
    pw = sync_playwright().start()
    browser = pw.chromium.launch(
        channel="chrome",  # use the installed system Chrome
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    return pw, browser


def new_context(browser: Browser) -> BrowserContext:
    return browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1366, "height": 900},
        locale="en-GB",
        timezone_id="Australia/Sydney",
    )


def dismiss_consent(page: Page) -> None:
    for sel in config.CONSENT_SELECTORS:
        try:
            loc = page.locator(sel)
            if loc.count():
                loc.first.click(timeout=5000)
                log.debug("Dismissed banner via %s", sel)
        except Exception:
            pass


def check_for_challenge(page: Page) -> None:
    """Detect bot-check / block interstitials and raise BotChallengeError."""
    try:
        title = (page.title() or "").lower()
    except Exception:
        title = ""
    if any(marker in title for marker in ("access denied", "just a moment")):
        raise BotChallengeError(f"challenge title: {title!r}")
    body = (page.content() or "").lower()
    hits = [m for m in config.CHALLENGE_MARKERS if m in body]
    # 'captcha' alone can false-positive; require two markers in that case
    strong = [m for m in hits if m != "captcha"]
    if strong or len(hits) >= 2:
        raise BotChallengeError(f"challenge markers: {hits}")
