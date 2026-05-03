"""Pipeline: source -> cache -> ai -> stream chunks back to caller."""
from __future__ import annotations

from typing import Iterator, Optional

from src.ai.base import AIProvider
from src.ai.tasks.base import Task
from src.core.models import CapturedText, TaskRequest
from src.sources.base import TextSource
from src.storage.cache import Cache


class Pipeline:
    def __init__(
        self,
        source: TextSource,
        task: Task,
        provider: AIProvider,
        cache: Cache,
        *,
        model: str,
        target_lang: str,
    ):
        self.source = source
        self.task = task
        self.provider = provider
        self.cache = cache
        self.model = model
        self.target_lang = target_lang

    def capture(self) -> Optional[CapturedText]:
        """Synchronous capture step. Call from the thread that has focus on
        the source application — typically the hotkey callback thread,
        BEFORE any popup is shown (showing a popup would steal focus and
        Ctrl+C would target the popup instead of the source app)."""
        return self.source.capture()

    def run(
        self,
        captured: Optional[CapturedText] = None,
        *,
        regenerate: bool = False,
    ) -> Iterator[str]:
        """Yield streaming result chunks for the given captured text.

        If `captured` is None, falls back to running `self.capture()` first
        (preserved for legacy callers / tests). Yields nothing when no text
        is available. Cache hits yield the full stored result as one chunk;
        cache misses stream from the AI provider and write back on completion.
        """
        if captured is None:
            captured = self.capture()
        if captured is None:
            return

        req = TaskRequest(
            text=captured.text,
            task=self.task.name,
            target_lang=self.target_lang,
            model=self.model,
        )

        if not regenerate:
            cached = self.cache.get(req)
            if cached is not None:
                self.cache.bump_hit(cached.cache_key)
                yield cached.result
                return

        messages = self.task.build_messages(captured.text, target_lang=self.target_lang)
        buf: list[str] = []
        for chunk in self.provider.stream(messages, model=self.model):
            buf.append(chunk)
            yield chunk

        full = "".join(buf).strip()
        if not full:
            return  # nothing to cache

        if regenerate:
            self.cache.regenerate(req, full)
        else:
            self.cache.put(req, full)
