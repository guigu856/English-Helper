"""Task abstraction: each task owns its prompt template and output expectations."""
from __future__ import annotations

from abc import ABC, abstractmethod

from src.ai.base import ChatMessage


class Task(ABC):
    name: str  # 'translate' / 'grammar' / ...

    @abstractmethod
    def build_messages(self, text: str, *, target_lang: str) -> list[ChatMessage]:
        raise NotImplementedError
