"""Core data models exchanged between layers."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class CapturedText:
    """Output of a TextSource."""
    text: str
    app: str = ""          # e.g. 'Code.exe', 'chrome.exe'
    lang: str = ""         # detected source language; optional
    context: str = ""      # surrounding sentence, optional (MVP: empty)


@dataclass
class TaskRequest:
    """Input to the AI layer."""
    text: str              # original, case preserved
    task: str              # 'translate' / 'grammar' / ...
    target_lang: str       # 'zh' / 'ja' / ...
    model: str

    def cache_key(self) -> str:
        """Lowercased + trimmed text; stable across case variants."""
        normalized = self.text.strip().lower()
        raw = f"{normalized}\x1f{self.task}\x1f{self.target_lang}\x1f{self.model}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass
class TaskResult:
    """Output from the AI layer (or cache)."""
    text: str              # original query text
    task: str
    target_lang: str
    model: str
    result: str            # rendered markdown / plain text
    cache_key: str
    is_starred: bool = False
    hit_count: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    from_cache: bool = False
