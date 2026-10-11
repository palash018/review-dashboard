# Azzurro Hotels — Booking.com Review Dashboard

A self-contained application that collects publicly available guest reviews
from four Azzurro Hotels properties on Booking.com, classifies them into
operational topics, and presents an operations-friendly dashboard for
non-technical staff.

**Documents**

| Document | For whom |
|---|---|
| [QUICKSTART.md](QUICKSTART.md) | Anyone setting it up — 3 copy-paste steps, no jargon |
| [USER_GUIDE.md](USER_GUIDE.md) | Operations staff — how to read and use the dashboard, zero technical terms |
| [docs/TUTORIAL.md](docs/TUTORIAL.md) | Guided tour with video + screenshots |
| README.md (this file) | Developers/evaluators — architecture, methodology, reliability, limitations |

**Live demo (read-only snapshot):** https://palash018.github.io/review-dashboard/ —
the full dashboard running entirely in the browser on the exported dataset;
run locally for live collection.

**Properties covered**

| Dashboard name          | Booking.com page                          |
|------------------------|-------------------------------------------|
| Olympic Hotel Paddington | booking.com/hotel/au/olympic-paddington |
| Potts Point            | booking.com/hotel/au/venus-potts-point-sydney |
| Central Sydney         | booking.com/hotel/au/venus-surry-hills    |
| Darling Harbour        | booking.com/hotel/au/chateau-de-venus     |

---

## Quick start

Requires **Python 3.12+** and **Node.js 20+ (22 recommended)** (Google Chrome must be installed
for the scraper).

```bash
# 1. Backend
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

# 2. Frontend (already-built copy ships in the repo, but rebuild if you like)
cd frontend && npm install && npm run build && cd ..

# 3. Run everything (API + dashboard on http://127.0.0.1:8000)
make demo            # or: cd backend && ../.venv/bin/python -m azzurro serve
```

The repository ships with a pre-collected dataset (`data/reviews.db`), so the
dashboard works immediately **without any scraping**.

### Daily use

```bash
make update                      # fetch new reviews, polite pacing (~1.5–2 min incl. ETA display)
make update ARGS=--fast          # trimmed delays (~1 min) — fine for daily refreshes
make update P=olympic-paddington # refresh a single property only
make demo                        # serve the refreshed dashboard
```

`update` still takes a minute or two even when nothing is new: it must load
each property page in a real browser (navigate → reviews tab → newest-first
→ first page → early-stop when no new reviews appear). Live progress lines
show per-property status and an ETA while it runs. `--fast` trims the polite
delays — slightly higher block risk, so keep full-speed backfills on the
default pacing.

### Collecting data yourself

```bash
make backfill        # full history for all 4 properties (~15–25 min)
make backfill P=olympic-paddington   # single property
make stats           # dataset summary
make export          # JSON export to data/reviews_export.json
make test            # run the test suite
make lint            # ruff (Python) + oxlint (frontend)
```

All commands also work directly:

```bash
cd backend
../.venv/bin/python -m azzurro scrape --mode update     # incremental
../.venv/bin/python -m azzurro scrape --mode backfill   # full history
../.venv/bin/python -m azzurro serve --port 8000
```

### Development mode (hot reload)

```bash
cd backend && ../.venv/bin/python -m azzurro serve --port 8000   # API only
cd frontend && npm run dev    # Vite dev server on :5173, proxies /api -> :8000
```

---

## Architecture

```
┌─────────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│ Playwright scraper   │────▶│ SQLite (reviews) │◀────│ FastAPI backend    │
│ (system Chrome)      │     │ data/reviews.db  │     │ /api/kpis|trends|… │
└─────────────────────┘     └──────────────────┘     └─────────┬─────────┘
                                                                 │
                                                     ┌──────────▼─────────┐
                                                     │ React dashboard     │
                                                     │ Vite+Tailwind+      │
                                                     │ Recharts (served by │
                                                     │ FastAPI in demo)    │
                                                     └────────────────────┘
```

- **Scraper** — `backend/azzurro/scraper/` (browser session, selectors, parser, collection loop)
- **Classification** — `backend/azzurro/classification/` (lexicons, keyword classifier, optional LLM)
- **Storage** — `backend/azzurro/database.py` (schema, dedup, run audit log)
- **API** — `backend/azzurro/api/` (aggregations + HTTP layer)
- **Frontend** — `frontend/src/` (components, filters, charts)

---

## How review collection works

Booking.com offers no public review API, so we render the **public hotel
pages** in a real browser (Playwright + locally installed Chrome) and read the
reviews section:

1. Open `https://www.booking.com/hotel/au/<slug>.en-gb.html` with a realistic
   user agent, `en-GB` locale and Sydney timezone.
2. Dismiss any consent banners, click the **Guest reviews** tab.
3. Sort reviews **newest first**, then paginate with the "Next page" button,
   parsing 10 reviews per page (`review-card` elements with stable
   `data-testid` attributes).
4. For each review we store: rating (1–10), title, the "Liked" and "Disliked"
   texts, review date, stay month, nights, room type, traveller type,
   reviewer name/country, and the hotel's response when present.

### Reliability engineering

| Concern | Mitigation |
|---|---|
| Duplicate reviews | Every review gets a stable content hash (property + reviewer + date + rating + title + text prefix) as primary key; inserts are idempotent upserts. Reviews are immutable once stored; if a guest edits a review on Booking.com it is stored as a new row |
| Partial failures | Each page is committed to SQLite immediately; a crash keeps everything collected so far; a run can simply be re-run |
| Bot challenges / blocks | Challenge interstitials are detected (title/body markers) and trigger exponential cooldowns and retries; the run then degrades gracefully to *partial* status instead of crashing |
| Page-load errors | Retries with backoff per pagination action (3×) and per property (3×); each property is isolated so one failure never blocks the others |
| Site redesigns | All DOM selectors live in one file (`scraper/selectors.py`); a Booking.com markup change is a one-file fix. Every run is recorded in `scrape_runs` (counts, new reviews, errors) so data gaps are visible via `/api/meta` |
| Run audit accuracy | Killed/crashed runs can't update their own status, so any stale `running` row is automatically marked `interrupted` when the next run starts — the audit log stays honest |
| Politeness | Jittered 2.5–6 s delay between pages, 10–25 s between properties (trimmable with `--fast`); only public `/hotel/*` pages are requested (robots.txt does not disallow them for generic agents); no internal AJAX endpoints are touched |
| Updating | `--mode update` re-scrapes newest-first and stops at the first page with no new reviews — typically 1 page per property (~10–15 s each) |

### Known limitations & assumptions

- **Terms of service**: scraping is technically against Booking.com's ToS.
  This project accesses only publicly visible pages, at polite rates, with no
  authentication bypass, for internal operational analysis. For production
  use, prefer an official partnership/API feed (e.g. Booking.com's
  Connectivity APIs) or a licensed review aggregator.
- **Coverage**: reviews require JavaScript rendering; if Booking.com deploys
  an aggressive bot wall (CAPTCHA on every load), collection pauses with a
  *partial* run status rather than producing corrupt data.
- **Dates**: we use the *review-submitted* date ("Reviewed: …") as the
  analytical date; the stay month is stored separately (`stay_period`).
- **Review counts**: only reviews visible while logged out (all pages of the
  public listing) are collected.
- **Anti-bot arms race**: selectors and challenge markers are stable today
  but are inherently fragile; the design isolates that fragility.
- **Personal data**: reviewer names/countries are public on the page; we keep
  them only for operational context and do not share them further.

---

## Review insights methodology

### Topic classification (hybrid)

**1. Keyword classifier (default, deterministic, offline).**
Each review is scanned against eight weighted lexicons — *cleanliness,
check-in, staff & reception, noise, facilities, location, room condition,
value for money* (including Australian/British spellings and common phrases
like "thin walls", "bed bugs", "check-in").

**Polarity per topic** exploits a structural gift: Booking.com already splits
every review into a **"Liked"** and **"Disliked"** section. A lexicon hit in
the disliked section is a negative mention of that topic, a hit in the liked
section a positive one. Negations ("not clean") inside the positive section
downgrade the polarity to *mixed*.

**Review sentiment** is anchored on the numeric rating: **≥ 8 → positive,
≤ 6 → negative**, in between neutral — except a long, substantive complaint
dragging a 7 down to negative.

**2. Optional LLM enrichment.** If `LLM_API_KEY` is set (any
OpenAI-compatible endpoint via `LLM_BASE_URL` / `LLM_MODEL`), reviews are
re-classified by an LLM in batches, with results **cached in the database**
(`classified_by='llm'`) so each review is processed at most once. Any error
silently falls back to keyword labels. No key is required for the demo.

### Insights output

The dashboard turns this into plain-English statements such as:

> *"Cleanliness — 41.7% of complaint reviews mentioned this (+24.3pp vs the
> previous period)"*

A **"complaint review"** = rating sentiment is negative **or** the disliked
section produced at least one negative/mixed topic mention. This deliberately
includes e.g. an 8/10 review that still complains about noise — operationally
that gripe matters even when the overall stay was good.

### Classification limitations

**Keyword-based (lexical) analysis is approximate by design.** It is fast,
deterministic, transparent (every tag shows the exact matched keywords on
hover) and works offline — but it can miss unusual phrasing, synonyms, typos
or sarcasm, and occasionally mis-tag a mention. The dashboard states this on
the insights panel so non-technical users know the tags are heuristic, not
ground truth.

**Setting `LLM_API_KEY` upgrades accuracy.** Reviews are then re-classified by
an LLM in batches (`cd backend && ../.venv/bin/python -m azzurro classify
--llm`), with results cached in the database so each review is processed at
most once. Any API error silently falls back to keyword labels.
The LLM path is covered by an offline test suite that mocks the
OpenAI-compatible endpoint (request shape, response parsing, error fallback,
caching — see `backend/tests/test_llm.py`).

- Topics can overlap ("shared bathroom" is both *facilities* and possibly
  *cleanliness*); we report every matching topic rather than forcing one.
- The 8 topics cover the requested operational areas; other themes (e.g.
  safety, wifi outages) roll into the nearest bucket or are uncategorised.

---

## Dashboard guide (for operations staff)

> See [USER_GUIDE.md](USER_GUIDE.md) for the full plain-language walkthrough.

- **KPI row** — average score, review volume, negative share and the sentiment
  mix for the **selected period**, compared against the immediately preceding
  period of the same length. With the "This week" preset this is exactly
  "current week vs previous week". Green = improving, red = worsening.
- **"What guests complained about"** — the top operational issues with
  period-over-period change (percentage points). Each topic is clickable and
  jumps to the review feed pre-filtered to that topic.
- **Property breakdown** — per-property score, change vs the previous period
  and each property's top issue (clickable, same cross-filter behaviour).
- **Empty-week fallback** — early in a new week (before any reviews arrive)
  the dashboard automatically shows the previous week with an amber notice
  instead of an empty screen; "Show current week anyway" switches back.
- **Trends** — weekly average score and positive/neutral/negative volumes.
- **Timezone selector** (top bar) — display timestamps and the "today" anchor
  for weekly stats in **Sydney / IST / UTC** time. Booking.com publishes only
  review *dates* (no times), so a review's date never shifts; what changes
  with the selector is (a) how UTC instants like the last-scrape time are
  shown, and (b) which calendar day counts as "today" for week boundaries —
  e.g. late Sunday UTC is already Monday in Sydney. Defaults to Sydney (the
  hotels' timezone) and is remembered per browser.
- **Review feed** — browse individual reviews; filter by property, period,
  topic, sentiment, full-text search; sort newest/oldest/lowest/highest.
  On a desktop, hovering a topic chip shows the exact matched keywords,
  so tags are never a black box.
- **Mobile** — the layout adapts to phones: filter chips become swipeable
  strips, cards stack vertically, and all touch targets are finger-sized.
- Ratings use Booking.com's familiar 1–10 scale ("scored 7.5").

---

## Testing & quality

```bash
make test    # 36 tests: parser, dedup, keyword classifier, LLM path (mocked), API aggregation/feed
make lint    # ruff + oxlint
```

## Project layout

```
QUICKSTART.md            3-step setup, no jargon
USER_GUIDE.md            plain-language guide for operations staff
backend/
  azzurro/
    __main__.py          CLI (scrape/classify/export/stats/serve)
    config.py            properties, politeness settings, thresholds
    database.py          schema, dedup, run audit
    scraper/             browser, selectors (single source), parser, collector
    classification/      lexicons, keyword classifier, optional LLM
    api/                 FastAPI app + aggregation service
  tests/                 pytest suite (36 tests)
frontend/                React + Vite + Tailwind + Recharts (works on phones)
data/reviews.db          pre-collected dataset (works offline)
Makefile                 one-command entry points
```
