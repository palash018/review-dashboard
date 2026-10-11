"""LLM enrichment tests against a mocked OpenAI-compatible endpoint.

No network or API key needed: httpx.post is monkeypatched with a fake that
returns realistic chat-completions payloads.
"""
import json as _json

import pytest

from azzurro.classification import llm as llm_mod
from azzurro.database import connect, init_db, review_id, upsert_review, utc_now_iso


class FakeResponse:
    def __init__(self, content: str):
        self._content = content

    def raise_for_status(self):
        pass

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def fake_post_factory(items_by_idx: dict[int, dict] | None = None,
                      raw_content: str | None = None,
                      error: Exception | None = None):
    """Return an httpx.post replacement capturing the request."""
    captured: dict = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = json
        if error:
            raise error
        if raw_content is not None:
            return FakeResponse(raw_content)
        body = json["messages"][1]["content"]
        n = len(body.strip().splitlines()) - 1  # numbered lines after the header
        results = [items_by_idx.get(i, {"idx": i, "sentiment": "neutral",
                                        "topics": []}) for i in range(n)]
        return FakeResponse(_json.dumps({"results": results}))

    fake_post.captured = captured
    return fake_post


def test_env_gating(monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    assert llm_mod.llm_available() is False
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    assert llm_mod.llm_available() is True


def test_classify_batch_happy_path(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    fake = fake_post_factory({0: {
        "idx": 0, "sentiment": "negative",
        "topics": [{"topic": "cleanliness", "polarity": "negative",
                    "keywords": ["dirty", "mould"]}]}
    })
    monkeypatch.setattr(llm_mod.httpx, "post", fake)

    batch = [{"rating": 4.0, "positive_text": None,
              "negative_text": "Dirty bathroom with mould"}]
    out = llm_mod._classify_batch(batch)

    assert out[0]["classified_by"] == "llm"
    assert out[0]["sentiment"] == "negative"
    topics = _json.loads(out[0]["topics_json"])
    assert topics[0]["topic"] == "cleanliness"
    assert topics[0]["keywords"] == ["dirty", "mould"]

    # request shape: correct endpoint, auth header, review text in prompt
    assert fake.captured["url"].endswith("/chat/completions")
    assert fake.captured["headers"]["Authorization"] == "Bearer sk-test"
    assert "Dirty bathroom with mould" in fake.captured["payload"]["messages"][1]["content"]
    assert fake.captured["payload"]["temperature"] == 0


def test_classify_batch_filters_unknown_topics(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    fake = fake_post_factory({0: {
        "idx": 0, "sentiment": "negative",
        "topics": [
            {"topic": "cleanliness", "polarity": "negative", "keywords": ["dirty"]},
            {"topic": "vibes", "polarity": "negative", "keywords": ["off"]},
        ]}
    })
    monkeypatch.setattr(llm_mod.httpx, "post", fake)
    out = llm_mod._classify_batch(
        [{"rating": 5.0, "positive_text": "", "negative_text": "dirty"}])
    topics = _json.loads(out[0]["topics_json"])
    assert [t["topic"] for t in topics] == ["cleanliness"]


def test_classify_batch_bare_array_response(monkeypatch):
    """Some endpoints ignore response_format; model may emit a bare array."""
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    raw = _json.dumps([{"idx": 0, "sentiment": "positive", "topics": []}])
    monkeypatch.setattr(llm_mod.httpx, "post",
                        fake_post_factory(raw_content=raw))
    out = llm_mod._classify_batch(
        [{"rating": 9.0, "positive_text": "lovely", "negative_text": None}])
    assert out[0]["classified_by"] == "llm"
    assert out[0]["sentiment"] == "positive"


def test_classify_batch_missing_item_raises(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    raw = _json.dumps({"results": []})  # empty -> missing item 0
    monkeypatch.setattr(llm_mod.httpx, "post",
                        fake_post_factory(raw_content=raw))
    with pytest.raises(ValueError):
        llm_mod._classify_batch(
            [{"rating": 9.0, "positive_text": "lovely", "negative_text": None}])


def test_in_pipe_fallback_on_api_error(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setattr(llm_mod.httpx, "post",
                        fake_post_factory(error=RuntimeError("api down")))
    rec = {"rating": 4.0, "positive_text": "ok",
           "negative_text": "Dirty bathroom"}
    out = llm_mod.classify_with_llm_fallback(rec)
    assert out["classified_by"] == "keyword"  # graceful degradation
    assert _json.loads(out["topics_json"])


def test_in_pipe_llm_used_when_available(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    fake = fake_post_factory({0: {"idx": 0, "sentiment": "negative",
                                   "topics": [{"topic": "noise",
                                               "polarity": "negative",
                                               "keywords": ["thin walls"]}]}})
    monkeypatch.setattr(llm_mod.httpx, "post", fake)
    rec = {"rating": 6.5, "positive_text": "fine",
           "negative_text": "Thin walls, could hear everything"}
    out = llm_mod.classify_with_llm_fallback(rec)
    assert out["classified_by"] == "llm"
    assert _json.loads(out["topics_json"])[0]["topic"] == "noise"


def _db_with_reviews(tmp_path, n=3):
    conn = connect(tmp_path / "llm.db")
    init_db(conn)
    for i in range(n):
        rec = {
            "id": review_id("potts-point", f"G{i}", f"2026-10-0{i + 1}", 5.0,
                            "T", f"dirty room {i}"),
            "property_slug": "potts-point", "reviewer_name": f"G{i}",
            "reviewer_country": None, "rating": 5.0, "title": "T",
            "positive_text": None, "negative_text": f"dirty room {i}",
            "review_date": f"2026-10-0{i + 1}", "stay_period": "2026-10",
            "nights": 1, "room_type": None, "traveler_type": None,
            "hotel_response": None, "sentiment": "negative",
            "topics_json": "[]", "classified_by": "keyword",
            "first_seen_at": utc_now_iso(), "collected_at": utc_now_iso(),
        }
        upsert_review(conn, rec)
    conn.commit()
    return conn


def test_enrich_unclassified_batches_and_caches(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    conn = _db_with_reviews(tmp_path, n=3)
    fake = fake_post_factory({0: {"idx": 0, "sentiment": "negative",
                                  "topics": [{"topic": "cleanliness",
                                              "polarity": "negative",
                                              "keywords": ["dirty"]}]},
                              1: {"idx": 1, "sentiment": "negative", "topics": []},
                              2: {"idx": 2, "sentiment": "negative", "topics": []}})
    monkeypatch.setattr(llm_mod.httpx, "post", fake)

    assert llm_mod.enrich_unclassified(conn) == 3
    assert conn.execute(
        "SELECT COUNT(*) FROM reviews WHERE classified_by='llm'").fetchone()[0] == 3
    assert conn.execute(
        "SELECT COUNT(*) FROM reviews WHERE sentiment='negative' AND "
        "topics_json != '[]'").fetchone()[0] == 1  # only idx 0 got topics

    # caching: second run re-tags nothing (skips already-LLM rows)
    assert llm_mod.enrich_unclassified(conn) == 0


def test_enrich_partial_failure_keeps_keyword_labels(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    conn = _db_with_reviews(tmp_path, n=2)
    monkeypatch.setattr(llm_mod.httpx, "post",
                        fake_post_factory(error=RuntimeError("503")))
    assert llm_mod.enrich_unclassified(conn) == 0
    assert conn.execute(
        "SELECT COUNT(*) FROM reviews WHERE classified_by='keyword'"
    ).fetchone()[0] == 2


def test_enrich_noop_without_key(tmp_path, monkeypatch):
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    conn = _db_with_reviews(tmp_path)
    assert llm_mod.enrich_unclassified(conn) == 0
