"""Tests for src.core.pipeline using fake source/provider (no network)."""
from __future__ import annotations

from typing import Iterator, Optional

import pytest

from src.ai.base import AIProvider, ChatMessage
from src.ai.tasks.translate import TranslateTask
from src.core.models import CapturedText
from src.core.pipeline import Pipeline
from src.sources.base import TextSource
from src.storage.cache import Cache
from src.storage.db import connect


class FakeSource(TextSource):
    def __init__(self, text: Optional[str]) -> None:
        self.text = text

    def capture(self) -> Optional[CapturedText]:
        if self.text is None:
            return None
        return CapturedText(text=self.text)


class FakeProvider(AIProvider):
    def __init__(self, chunks: list[str]) -> None:
        self.chunks = chunks
        self.calls = 0

    def stream(self, messages: list[ChatMessage], *, model: str) -> Iterator[str]:
        self.calls += 1
        for c in self.chunks:
            yield c


@pytest.fixture
def cache(tmp_path):
    conn = connect(tmp_path / "p.db")
    yield Cache(conn)
    conn.close()


def _pipeline(source, provider, cache):
    return Pipeline(
        source=source,
        task=TranslateTask(),
        provider=provider,
        cache=cache,
        model="m1",
        target_lang="zh",
    )


def test_no_capture_yields_nothing(cache):
    p = _pipeline(FakeSource(None), FakeProvider(["x"]), cache)
    assert list(p.run()) == []


def test_miss_calls_provider_and_caches(cache):
    provider = FakeProvider(["**hello**", " world"])
    p = _pipeline(FakeSource("hello"), provider, cache)
    out = list(p.run())
    assert out == ["**hello**", " world"]
    assert provider.calls == 1

    # second run hits cache
    p2 = _pipeline(FakeSource("hello"), provider, cache)
    out2 = list(p2.run())
    assert out2 == ["**hello** world"]
    assert provider.calls == 1  # unchanged


def test_cache_hit_bumps_count(cache):
    provider = FakeProvider(["x"])
    p = _pipeline(FakeSource("term"), provider, cache)
    list(p.run())   # miss -> stored
    list(p.run())   # hit -> bump

    from src.core.models import TaskRequest
    req = TaskRequest(text="term", task="translate", target_lang="zh", model="m1")
    got = cache.get(req)
    assert got.hit_count == 2


def test_regenerate_overwrites(cache):
    p1 = _pipeline(FakeSource("term"), FakeProvider(["v1"]), cache)
    list(p1.run())

    new_provider = FakeProvider(["v2-new"])
    p2 = _pipeline(FakeSource("term"), new_provider, cache)
    out = list(p2.run(regenerate=True))
    assert out == ["v2-new"]
    assert new_provider.calls == 1

    # subsequent normal run should now hit the regenerated value
    p3 = _pipeline(FakeSource("term"), FakeProvider(["should-not-be-called"]), cache)
    assert list(p3.run()) == ["v2-new"]


def test_case_insensitive_cache(cache):
    list(_pipeline(FakeSource("Bank"), FakeProvider(["银行"]), cache).run())
    second = FakeProvider(["should-not-be-called"])
    out = list(_pipeline(FakeSource("bank"), second, cache).run())
    assert out == ["银行"]
    assert second.calls == 0
