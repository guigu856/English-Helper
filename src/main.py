"""Entry point — Phase 3: hotkey + clipboard + pipeline + PyQt popup.

Press the configured hotkey (default F8) after selecting English text
in any app. The translation appears in a floating popup near your cursor.
"""
from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

# Ensure cwd is the project root regardless of how we were launched (the
# Windows Run-registry autostart hook starts processes in C:\Windows\system32,
# which would break relative paths like config.yaml and data/english-helper.db).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(_PROJECT_ROOT)

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from . import __version__
from .ai.openai_compat import OpenAICompatibleProvider
from .ai.tasks.translate import TranslateTask
from .app import HotkeyBridge
from .config import Config, ConfigError
from .core.hotkey import HotkeyManager
from .core.pipeline import Pipeline
from .sources.clipboard import ClipboardSource
from .storage.cache import Cache
from .storage.db import connect
from .ui.popup import PopupWindow
from .ui.tray import TrayIcon


def main() -> int:
    print(f"English Helper v{__version__}")
    try:
        cfg = Config.load()
    except ConfigError as e:
        print(f"[config error] {e}")
        return 1

    conn = connect(cfg.storage.db_path)
    cache = Cache(conn)
    provider = OpenAICompatibleProvider(base_url=cfg.ai.base_url, api_key=cfg.ai.api_key)
    pipeline = Pipeline(
        source=ClipboardSource(),
        task=TranslateTask(),
        provider=provider,
        cache=cache,
        model=cfg.ai.model,
        target_lang=cfg.language.target,
    )

    app = QApplication(sys.argv)
    # Keep the event loop alive even when no window is visible (we run from tray
    # / hotkey and have no main window).
    app.setQuitOnLastWindowClosed(False)

    popup = PopupWindow(pipeline)

    bridge = HotkeyBridge(pipeline)
    bridge.captured.connect(popup.show_with_capture)
    bridge.no_selection.connect(popup.show_no_selection)

    hotkeys = HotkeyManager()
    hotkeys.register(cfg.hotkey.translate, bridge.on_hotkey)

    def on_toggle_pause(paused: bool) -> None:
        if paused:
            hotkeys.unregister(cfg.hotkey.translate)
        else:
            hotkeys.register(cfg.hotkey.translate, bridge.on_hotkey)

    tray = TrayIcon(
        app=app,
        hotkey_text=cfg.hotkey.translate,
        on_toggle_pause=on_toggle_pause,
        version=__version__,
    )
    tray.show()

    print(f"Hotkey registered: {cfg.hotkey.translate}")
    print(f"Model: {cfg.ai.model}  Target: {cfg.language.target}  DB: {cfg.storage.db_path}")
    print("Select English text and press the hotkey. Use the tray icon to pause or quit.")

    # Make Ctrl+C in the console reliably quit the Qt event loop.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    # Wake the event loop periodically so Python can process the signal.
    tick = QTimer()
    tick.start(200)
    tick.timeout.connect(lambda: None)

    try:
        exit_code = app.exec()
    finally:
        hotkeys.clear()
        conn.close()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
