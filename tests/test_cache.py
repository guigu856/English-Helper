"""Tests for src.storage.cache."""
from __future__ import annotations

import pytest

from src.core.models import TaskRequest
from src.storage.cache import Cache
from src.storage.db import connect


@pytest.fixture
def cache(tmp_path):
    conn = connect(tmp_path / "test.db")
    yield Cache(conn)
    conn.close()


def _req(text="Bank", task="translate", lang="zh", model="m1") -> TaskRequest:
    return TaskRequest(text=text, task=task, target_lang=lang, model=model)


def test_cache_key_normalizes_case_and_whitespace():
    a = _req(text="  Bank  ").cache_key()
    b = _req(text="bank").cache_key()
    assert a == b


def test_cache_key_differs_by_task_and_model():
    base = _req().cache_key()
    assert base != _req(task="grammar").cache_key()
    assert base != _req(model="m2").cache_key()
    assert base != _req(lang="ja").cache_key()


def test_miss_then_put_then_hit(cache):
    req = _req(text="ephemeral")
    assert cache.get(req) is None
    stored = cache.put(req, "short-lived")
    assert stored.from_cache is False
    assert stored.result == "short-lived"

    got = cache.get(req)
    assert got is not None
    assert got.from_cache is True
    assert got.result == "short-lived"
    assert got.text == "ephemeral"  # original case preserved


def test_bump_hit_increments(cache):
    req = _req(text="run")
    cache.put(req, "r1")
    key = req.cache_key()
    cache.bump_hit(key)
    cache.bump_hit(key)
    got = cache.get(req)
    assert got.hit_count == 3  # 1 from insert + 2 bumps


def test_regenerate_overwrites_result(cache):
    req = _req(text="bank")
    cache.put(req, "old")
    cache.bump_hit(req.cache_key())  # hit_count = 2
    refreshed = cache.regenerate(req, "new")
    assert refreshed.result == "new"
    assert refreshed.from_cache is False
    # hit_count preserved across regenerate
    got = cache.get(req)
    assert got.result == "new"
    assert got.hit_count == 2


def test_regenerate_inserts_when_missing(cache):
    req = _req(text="novel")
    result = cache.regenerate(req, "freshly-made")
    assert result.result == "freshly-made"
    assert cache.get(req).result == "freshly-made"


def test_put_is_idempotent_on_conflict(cache):
    """A second put for the same key updates result without raising,
    preserving hit_count and is_starred."""
    req = _req(text="dup")
    cache.put(req, "v1")
    cache.bump_hit(req.cache_key())  # hit_count = 2
    # Simulate a star, then a racing concurrent put with a different result.
    cache.conn.execute(
        "UPDATE queries SET is_starred = 1 WHERE cache_key = ?",
        (req.cache_key(),),
    )
    cache.conn.commit()

    second = cache.put(req, "v2")
    assert second.result == "v2"
    assert second.hit_count == 2  # not reset
    assert second.is_starred is True  # not reset


def test_case_preservation_in_storage(cache):
    req = _req(text="Apple")
    cache.put(req, "water")
    # Query with different case should still hit (normalized key)
    hit = cache.get(_req(text="apple"))
    assert hit is not None
    # But the stored text keeps the original casing of the first insertion
    assert hit.text == "Apple"
