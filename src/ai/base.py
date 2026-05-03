"""AIProvider abstraction.

Providers return streaming text chunks (plain strings).
Implementations wrap vendor SDKs and must NOT leak vendor-specific types upward.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Iterator


@dataclass
class ChatMessage:
    role: str   # 'system' | 'user' | 'assistant'
    content: str


class AIProvider(ABC):
    @abstractmethod
    def stream(self, messages: list[ChatMessage], *, model: str) -> Iterator[str]:
        """Yield incremental text chunks. Consumers join them to form full reply."""
        raise NotImplementedError
