"""HotkeyManager: register global hotkeys and dispatch callbacks.

Uses the `keyboard` library, which installs a low-level Windows hook.
Notes:
- On some systems requires running as Administrator to receive events from
  elevated apps. For non-elevated targets it works without admin.
- Callbacks run on the keyboard library's event thread; consumers must not
  block long. UI work should be marshalled to the GUI thread.
"""
from __future__ import annotations

from typing import Callable, Dict

import keyboard


Callback = Callable[[], None]


class HotkeyManager:
    def __init__(self) -> None:
        self._handles: Dict[str, object] = {}

    def register(self, hotkey: str, callback: Callback) -> None:
        """Register a hotkey. If already registered, replace the binding."""
        self.unregister(hotkey)
        # suppress=False so the hotkey is not consumed (lets users e.g. still
        # use Ctrl+Alt+D for app shortcuts if any).
        handle = keyboard.add_hotkey(hotkey, callback, suppress=False)
        self._handles[hotkey] = handle

    def unregister(self, hotkey: str) -> None:
        handle = self._handles.pop(hotkey, None)
        if handle is not None:
            try:
                keyboard.remove_hotkey(handle)
            except (KeyError, ValueError):
                pass

    def clear(self) -> None:
        for hk in list(self._handles):
            self.unregister(hk)

    def wait(self) -> None:
        """Block forever until process exits or Ctrl+C in console."""
        keyboard.wait()
