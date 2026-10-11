"""Optional LLM enrichment (env-gated, OpenAI-compatible).

Only used when LLM_API_KEY is set; results are cached in the DB
(classified_by='llm') so each review is billed at most once. Any error
falls back to the deterministic keyword classifier.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

from .keyword import classify_record
from .lexicons import TOPICS

log = logging.getLogger(__name__)

TOPIC_LIST = ", ".join(TOPICS.keys())

SYSTEM_PROMPT = (
    "You classify hotel guest reviews for an operations team. "
    f"Assign topics from exactly this list: {TOPIC_LIST}. "
    "For each topic present, give polarity 'positive' or 'negative' and quote "
    "up to 3 supporting keywords from the review. Also give an overall "
    "sentiment: 'positive', 'neutral' or 'negative'. "
    "Respond with strict JSON only."
)


def llm_available() -> bool:
    return bool(os.environ.get("LLM_API_KEY"))


def _parse_response(text: str, expected: int) -> list[dict[str, Any]]:
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        raise ValueError("no JSON array in LLM response")
    items = json.loads(m.group(0))
    if not isinstance(items, list) or len(items) != expected:
        raise ValueError(f"expected {expected} items, got {len(items)}")
    return items


def _classify_batch(batch: list[dict[str, Any]]) -> list[dict[str, Any]]:
    api_key = os.environ["LLM_API_KEY"]
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    lines = []
    for i, r in enumerate(batch):
        lines.append(
            f"{i}. rating={r.get('rating')} liked: {r.get('positive_text') or '-'} "
            f"| disliked: {r.get('negative_text') or '-'}"
        )
    payload = {
        "model": model,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": (
                "Classify each review. Return JSON like "
                '{"results":[{"idx":0,"sentiment":"negative","topics":'
                '[{"topic":"cleanliness","polarity":"negative","keywords":["dirty"]}]}]}\n'
                + "\n".join(lines))},
        ],
    }
    resp = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = None
    # models may answer with {"results": [...]} or a bare [...] array
    items = data.get("results") if isinstance(data, dict) else None
    if not items:
        items = _parse_response(content, len(batch))

    out = []
    for i, r in enumerate(batch):
        item = next((it for it in items if it.get("idx") == i), None)
        if not item:
            raise ValueError(f"missing item {i} in LLM response")
        topics = [
            {"topic": t["topic"], "polarity": t.get("polarity", "mixed"),
             "keywords": t.get("keywords", [])[:3]}
            for t in item.get("topics", []) if t.get("topic") in TOPICS
        ]
        order = {"negative": 0, "mixed": 1, "positive": 2}
        topics.sort(key=lambda t: (order.get(t["polarity"], 3), t["topic"]))
        out.append({
            **r,
            "sentiment": item.get("sentiment", r.get("sentiment", "neutral")),
            "topics_json": json.dumps(topics),
            "classified_by": "llm",
        })
    return out


def enrich_unclassified(conn, limit: int = 500) -> int:
    """Re-tag stored reviews with the LLM (skips already-LLM rows)."""
    if not llm_available():
        log.info("LLM_API_KEY not set - skipping LLM enrichment")
        return 0
    rows = conn.execute(
        "SELECT id, property_slug, rating, positive_text, negative_text, "
        "sentiment, topics_json, classified_by FROM reviews "
        "WHERE classified_by != 'llm' ORDER BY review_date DESC LIMIT ?", (limit,)
    ).fetchall()
    batch: list[dict[str, Any]] = []
    done = 0
    for row in rows:
        batch.append(dict(row))
        if len(batch) == 20:
            done += _process_batch(conn, batch)
            batch = []
    if batch:
        done += _process_batch(conn, batch)
    return done


def _process_batch(conn, batch: list[dict[str, Any]]) -> int:
    try:
        enriched = _classify_batch(batch)
    except Exception as exc:
        log.warning("LLM batch failed (%s); keeping keyword labels", exc)
        return 0
    for rec in enriched:
        conn.execute(
            "UPDATE reviews SET sentiment=?, topics_json=?, classified_by=? "
            "WHERE id=?",
            (rec["sentiment"], rec["topics_json"], rec["classified_by"], rec["id"]),
        )
    conn.commit()
    return len(enriched)


def classify_with_llm_fallback(record: dict[str, Any]) -> dict[str, Any]:
    """In-pipe classifier: LLM when possible (single review), else keywords."""
    if llm_available():
        try:
            return _process_batch_silent(record)
        except Exception:
            pass
    return classify_record(record)


def _process_batch_silent(record: dict[str, Any]) -> dict[str, Any]:
    enriched = _classify_batch([{**record, "id": record.get("id", "0"), "idx": 0}])
    out = enriched[0]
    record.update({k: out[k] for k in ("sentiment", "topics_json", "classified_by")})
    return record
