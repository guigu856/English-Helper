"""Background worker that runs the pipeline and emits chunks as Qt signals.

Keeps AI/network I/O off the GUI thread. Uses pyqtSignal for cross-thread
delivery — Qt marshals the emit to the receiving widget's (GUI) thread.
"""
from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from src.ai.openai_compat import AIProviderError
from src.core.models import CapturedText
from src.core.pipeline import Pipeline


class StreamWorker(QThread):
    chunk = pyqtSignal(str)
    finished_ok = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(
        self,
        pipeline: Pipeline,
        captured: CapturedText,
        *,
        regenerate: bool = False,
    ):
        super().__init__()
        self.pipeline = pipeline
        self.captured = captured
        self.regenerate = regenerate

    def run(self) -> None:
        try:
            for part in self.pipeline.run(self.captured, regenerate=self.regenerate):
                self.chunk.emit(part)
            self.finished_ok.emit()
        except AIProviderError as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001 — UI shows user-facing message
            self.failed.emit(f"Unexpected error: {e}")
