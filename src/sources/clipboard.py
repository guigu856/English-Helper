"""ClipboardSource: simulate Ctrl+C to read selection, then restore clipboard.

Trade-offs:
- Works in virtually any Windows app that supports Ctrl+C copy.
- After capture, the user's previous clipboard text is restored so they can
  still paste whatever they had before triggering us.
- The captured word will inevitably show up once in Windows clipboard history
  (Win+V); this is a Windows limitation — apps cannot suppress that record
  because the target app writes the clipboard in response to Ctrl+C before
  we get a chance to touch it.
- Non-text clipboard formats (image/file) are lost; we only preserve text.

Important: when invoked from a global hotkey callback, the user's modifier
keys (Ctrl/Alt/Shift/Win) are still physically held down at the moment the
callback fires. Sending `ctrl+c` directly would actually deliver something
like `Ctrl+Alt+C` to the foreground app, which isn't a copy. We release all
modifiers first and wait briefly for the OS to register the release.
"""
from __future__ import annotations

import time
from typing import Optional

import keyboard
import pyperclip

from src.core.models import CapturedText
from .base import TextSource


# Time to wait after releasing modifier keys before sending Ctrl+C.
MODIFIER_RELEASE_WAIT_SEC = 0.05
# Time to let the foreground app respond to Ctrl+C and update the clipboard.
# 120ms is comfortably enough for native apps; web apps may need a tad more.
COPY_WAIT_SEC = 0.15
# Tiny delay before restoring so slow targets finish writing to clipboard first.
RESTORE_DELAY_SEC = 0.05

_MODIFIERS = ("ctrl", "alt", "shift", "windows", "left ctrl", "right ctrl",
              "left alt", "right alt", "left shift", "right shift",
              "left windows", "right windows")


def _release_modifiers() -> None:
    """Release any modifier keys that may still be physically held by the user."""
    for key in _MODIFIERS:
        try:
            keyboard.release(key)
        except Exception:
            pass


def _safe_paste() -> str:
    """pyperclip.paste, never raising — returns empty string on failure."""
    try:
        return pyperclip.paste() or ""
    except Exception:
        return ""


def _safe_copy(text: str) -> None:
    """pyperclip.copy, never raising."""
    try:
        pyperclip.copy(text)
    except Exception:
        pass


class ClipboardSource(TextSource):
    def capture(self) -> Optional[CapturedText]:
        # Back up whatever the user currently has in the clipboard.
        backup = _safe_paste()
        # Clear clipboard so we can detect "nothing was selected" reliably.
        _safe_copy("")

        _release_modifiers()
        time.sleep(MODIFIER_RELEASE_WAIT_SEC)

        keyboard.send("ctrl+c")
        time.sleep(COPY_WAIT_SEC)

        captured = _safe_paste()

        # Restore the user's previous clipboard text.
        time.sleep(RESTORE_DELAY_SEC)
        _safe_copy(backup)

        text = captured.strip()
        if not text:
            return None
        return CapturedText(text=text)
