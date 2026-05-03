"""TextSource abstraction: how we get the text the user wants translated."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.core.models import CapturedText


class TextSource(ABC):
    @abstractmethod
    def capture(self) -> Optional[CapturedText]:
        """Return captured text, or None if nothing meaningful was selected."""
        raise NotImplementedError
