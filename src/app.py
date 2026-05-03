"""Qt application wiring: bridge hotkey (background thread) -> popup (GUI thread).

Uses a QObject with pyqtSignals so the `keyboard` callback can request a
popup from its own thread and Qt will deliver the slot invocation on the
GUI thread automatically.

CRITICAL: text capture (Ctrl+C simulation) MUST happen on the hotkey thread
BEFORE any popup is shown. Showing a popup activates it and steals focus
away from the source application — sending Ctrl+C after that would target
our popup and capture nothing. So the bridge:
  1. (hotkey thread) calls pipeline.capture() while source app still has focus
  2. emits a signal carrying the result
  3. (GUI thread) shows popup with the captured text (or "no selection")
"""
from __future__ import annotations

import threading

from PyQt6.QtCore import QObject, pyqtSignal

from .core.models import CapturedText
from .core.pipeline import Pipeline


class HotkeyBridge(QObject):
    captured = pyqtSignal(CapturedText)
    no_selection = pyqtSignal()

    def __init__(self, pipeline: Pipeline):
        super().__init__()
        self.pipeline = pipeline
        # Drop hotkey presses that arrive while a previous capture is still
        # running, so a fast double-press doesn't queue two clipboard probes.
        self._busy = threading.Lock()

    def on_hotkey(self) -> None:
        """Called from the keyboard library's background thread."""
        if not self._busy.acquire(blocking=False):
            return
        try:
            captured = self.pipeline.capture()
        finally:
            self._busy.release()
        if captured is None:
            self.no_selection.emit()
        else:
            self.captured.emit(captured)
