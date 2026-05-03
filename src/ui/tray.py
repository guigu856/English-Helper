"""System tray icon: pause toggle, about, quit.

The tray keeps the app discoverable when no popup is on screen. Without a
tray, a hotkey-only app is invisible to users — they can't tell whether
it's running or how to quit it.

Icon is generated in-memory with QPainter so we don't need a resource file.
"""
from __future__ import annotations

from typing import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from src import autostart


def _make_tray_icon(letter: str = "E", size: int = 64) -> QIcon:
    """Render a circular monogram icon at runtime."""
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#3b82f6"))
    p.drawEllipse(0, 0, size, size)
    p.setPen(QColor("#ffffff"))
    font = QFont("Segoe UI")
    font.setBold(True)
    font.setPixelSize(int(size * 0.55))
    p.setFont(font)
    p.drawText(pix.rect(), Qt.AlignmentFlag.AlignCenter, letter)
    p.end()
    return QIcon(pix)


class TrayIcon(QSystemTrayIcon):
    """Tray icon with a pause toggle, about, and quit actions.

    `on_toggle_pause(paused: bool)` is invoked when the user toggles pause —
    callers should unregister/re-register the global hotkey accordingly.
    """

    def __init__(
        self,
        *,
        app: QApplication,
        hotkey_text: str,
        on_toggle_pause: Callable[[bool], None],
        version: str,
    ):
        super().__init__(_make_tray_icon())
        self._app = app
        self._on_toggle_pause = on_toggle_pause
        self._hotkey_text = hotkey_text
        self._version = version

        self.setToolTip(f"English Helper · {hotkey_text}")

        menu = QMenu()
        self._act_pause = QAction("暂停热键", menu, checkable=True)
        self._act_pause.toggled.connect(self._handle_pause_toggled)
        menu.addAction(self._act_pause)

        self._act_autostart = QAction("开机自启", menu, checkable=True)
        self._act_autostart.setChecked(autostart.is_enabled())
        self._act_autostart.toggled.connect(self._handle_autostart_toggled)
        menu.addAction(self._act_autostart)

        menu.addSeparator()

        act_about = QAction("关于", menu)
        act_about.triggered.connect(self._show_about)
        menu.addAction(act_about)

        act_quit = QAction("退出", menu)
        act_quit.triggered.connect(self._app.quit)
        menu.addAction(act_quit)

        self.setContextMenu(menu)
        self.activated.connect(self._handle_activated)

    # ---- handlers ----

    def _handle_pause_toggled(self, checked: bool) -> None:
        # Reflect state in tooltip so users see at a glance whether hotkey is live.
        suffix = "（已暂停）" if checked else self._hotkey_text
        self.setToolTip(f"English Helper · {suffix}")
        self._on_toggle_pause(checked)

    def _handle_autostart_toggled(self, checked: bool) -> None:
        try:
            if checked:
                autostart.enable()
            else:
                autostart.disable()
        except OSError as e:
            # Revert the checkbox state and tell the user what went wrong.
            self._act_autostart.blockSignals(True)
            self._act_autostart.setChecked(not checked)
            self._act_autostart.blockSignals(False)
            QMessageBox.warning(None, "English Helper", f"无法修改开机自启：{e}")

    def _handle_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_about()

    def _show_about(self) -> None:
        QMessageBox.information(
            None,
            "English Helper",
            f"<h3>English Helper v{self._version}</h3>"
            f"<p>选中英文 → 按 <b>{self._hotkey_text}</b> → AI 翻译浮窗</p>"
            f"<p style='color:#888'>双击托盘图标可重新打开此窗口。</p>",
        )
