"""Floating translation popup near the mouse cursor.

Close behavior:
- X button, ESC key, and focus-out all close the popup.
- Focus-out is suppressed while the mouse is hovering over the popup, so
  the user can reach for a button (copy/regenerate) without the popup
  vanishing under them.
- A "regenerate" button forces bypassing the cache.

Markdown rendering uses QTextDocument.setMarkdown (available since Qt 5.14;
stable in Qt6). We update it with the running text each chunk — simpler and
plenty fast for our message sizes (<2KB).
"""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QCursor, QGuiApplication, QKeyEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from src.core.models import CapturedText
from src.core.pipeline import Pipeline
from src.ui.worker import StreamWorker


# Spacing scale: everything is a multiple of 4px.
SP_1, SP_2, SP_3, SP_4 = 4, 8, 12, 16

POPUP_WIDTH = 440
POPUP_MIN_HEIGHT = 140
POPUP_MAX_HEIGHT = 520
CURSOR_OFFSET = QPoint(SP_4, SP_4)

# Visual tokens (dark surface + amber accent for IPA + blue for word classes).
COLOR_BG = "#1f2430"
COLOR_BORDER = "#2f3646"
COLOR_TITLE = "#8b93a7"
COLOR_BODY = "#e2e8f0"
COLOR_MUTED = "#8b93a7"
COLOR_ACCENT = "#60a5fa"   # blue — word classes
COLOR_IPA = "#fbbf24"      # amber — phonetic
COLOR_QUOTE_BG = "#262c3a"
COLOR_SELECT = "#3b82f6"

# Widget-level stylesheet (frame, buttons, browser container).
STYLE = f"""
QWidget#popupRoot {{
    background-color: {COLOR_BG};
    border: 1px solid {COLOR_BORDER};
    border-radius: 10px;
}}
QLabel#title {{
    color: {COLOR_TITLE};
    font-size: 11px;
    letter-spacing: 0.3px;
}}
QPushButton {{
    background: transparent;
    color: {COLOR_MUTED};
    border: none;
    padding: {SP_1}px {SP_2}px;
    border-radius: {SP_1}px;
    min-width: 20px;
    font-size: 13px;
}}
QPushButton:hover {{
    background-color: #2d3344;
    color: #ffffff;
}}
QTextBrowser {{
    background-color: transparent;
    color: {COLOR_BODY};
    border: none;
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 14px;
    selection-background-color: {COLOR_SELECT};
}}
"""

TITLE_MAX_LEN = 40


def _truncate(s: str, limit: int = TITLE_MAX_LEN) -> str:
    """Return s untouched if short enough, else trimmed with an ellipsis."""
    return s if len(s) <= limit else s[: limit - 3] + "..."


# Rich-text stylesheet applied to the QTextDocument inside the QTextBrowser,
# so we can style each markdown element (IPA as h3, word classes as <strong>,
# quoted translation as <blockquote>, etc.) without inline HTML.
DOC_STYLESHEET = f"""
h3 {{
    color: {COLOR_IPA};
    font-family: "Cambria", "Georgia", serif;
    font-size: 16px;
    font-weight: 500;
    margin: 0 0 8px 0;
}}
p {{
    margin: 6px 0;
    line-height: 1.45;
}}
strong {{
    color: {COLOR_ACCENT};
    font-weight: 600;
}}
ul {{
    margin: 4px 0 8px 0;
    padding-left: 20px;
}}
li {{
    color: {COLOR_BODY};
    margin: 2px 0;
}}
blockquote {{
    color: {COLOR_BODY};
    background-color: {COLOR_QUOTE_BG};
    border-left: 3px solid {COLOR_ACCENT};
    margin: 6px 0;
    padding: 6px 10px;
}}
"""


class PopupWindow(QWidget):
    def __init__(self, pipeline: Pipeline):
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.pipeline = pipeline
        self._worker: Optional[StreamWorker] = None
        self._hovering = False
        self._pending_close = False
        self._buf = ""
        self._last_captured: Optional[CapturedText] = None

        # Loading animation: animated ellipsis while waiting for first chunk.
        self._loading_dots = 0
        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(350)
        self._loading_timer.timeout.connect(self._tick_loading)

        self.setObjectName("popupRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFixedWidth(POPUP_WIDTH)
        self.setStyleSheet(STYLE)

        self._build_ui()

    # ---- UI ----

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(SP_3, SP_2, SP_3, SP_3)
        root.setSpacing(SP_1)

        # Header: title + buttons
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(SP_1)
        self.title = QLabel("English Helper")
        self.title.setObjectName("title")
        header.addWidget(self.title)
        header.addStretch(1)

        self.btn_regen = QPushButton("↻")
        self.btn_regen.setToolTip("重新生成（跳过缓存）")
        self.btn_regen.clicked.connect(self._on_regenerate)
        header.addWidget(self.btn_regen)

        self.btn_close = QPushButton("✕")
        self.btn_close.setToolTip("关闭（Esc）")
        self.btn_close.clicked.connect(self.hide)
        header.addWidget(self.btn_close)
        root.addLayout(header)

        # Body (rich text). Default stylesheet styles markdown-rendered elements.
        self.body = QTextBrowser(self)
        self.body.setOpenExternalLinks(True)
        self.body.setMinimumHeight(POPUP_MIN_HEIGHT)
        self.body.setMaximumHeight(POPUP_MAX_HEIGHT)
        self.body.document().setDefaultStyleSheet(DOC_STYLESHEET)
        root.addWidget(self.body)

    # ---- Public API ----

    def show_with_capture(self, captured: CapturedText, *, regenerate: bool = False) -> None:
        """Show the popup near the cursor and start streaming a translation
        for the given pre-captured text."""
        self._cancel_worker()
        self._buf = ""
        self._last_captured = captured
        self._set_title_for(captured)
        # Placeholder body renders an animated ellipsis until the first chunk.
        self._start_loading()
        self._show_at_cursor()

        self._worker = StreamWorker(self.pipeline, captured, regenerate=regenerate)
        self._worker.chunk.connect(self._on_chunk)
        self._worker.finished_ok.connect(self._on_finished_ok)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    def show_no_selection(self) -> None:
        """Show a 'nothing was selected' message."""
        self._cancel_worker()
        self._last_captured = None
        self.title.setText("No selection")
        self.body.setPlainText(
            "没有取到选中文本。请先在任意应用里选中英文再按热键。\n"
            "（在经典 cmd 终端里可能无效，推荐 Windows Terminal）"
        )
        self._show_at_cursor()

    # ---- worker slots ----

    def _on_chunk(self, s: str) -> None:
        self._stop_loading()
        self._buf += s
        self.body.setMarkdown(self._buf)
        # auto-scroll to bottom as stream grows
        sb = self.body.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_finished_ok(self) -> None:
        self._stop_loading()
        if self._last_captured is not None:
            self._set_title_for(self._last_captured, prefix="")
        else:
            self.title.setText("English Helper")

    def _on_failed(self, msg: str) -> None:
        self._stop_loading()
        self.title.setText("Error")
        self.body.setPlainText(msg)

    # ---- loading animation ----

    def _start_loading(self) -> None:
        self._loading_dots = 0
        self._render_loading()
        self._loading_timer.start()

    def _stop_loading(self) -> None:
        if self._loading_timer.isActive():
            self._loading_timer.stop()

    def _tick_loading(self) -> None:
        self._loading_dots = (self._loading_dots + 1) % 4
        self._render_loading()

    def _render_loading(self) -> None:
        dots = "•" * self._loading_dots + "∙" * (3 - self._loading_dots)
        self.body.setHtml(
            f'<div style="color:{COLOR_MUTED};font-size:13px;padding:8px 2px;">'
            f"思考中 {dots}</div>"
        )

    # ---- title helper ----

    def _set_title_for(self, captured: CapturedText, *, prefix: str = "… ") -> None:
        self.title.setText(f"{prefix}{_truncate(captured.text)}")

    def _show_at_cursor(self) -> None:
        """Position, show, raise and focus the popup."""
        self._position_near_cursor()
        self.show()
        self.activateWindow()
        self.raise_()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    # ---- interactions ----

    def _on_regenerate(self) -> None:
        # Bypass cache and re-stream using the *previously captured* text.
        # We do NOT re-capture, because the user is now hovering our popup
        # rather than the original source app.
        if self._last_captured is None:
            return
        self.show_with_capture(self._last_captured, regenerate=True)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(e)

    def enterEvent(self, e) -> None:
        self._hovering = True
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self._hovering = False
        if self._pending_close:
            self._pending_close = False
            self.hide()
        super().leaveEvent(e)

    def focusOutEvent(self, e) -> None:
        # If user is pointing at the popup (about to click a button), defer
        # closing until mouse leaves. Otherwise close immediately.
        if self._hovering:
            self._pending_close = True
        else:
            self.hide()
        super().focusOutEvent(e)

    def hideEvent(self, e) -> None:
        self._stop_loading()
        self._cancel_worker()
        super().hideEvent(e)

    # ---- helpers ----

    def _cancel_worker(self) -> None:
        w = self._worker
        if w is not None and w.isRunning():
            # Let it finish naturally; pipeline runs are short. Disconnect so
            # slots on a possibly-hidden popup don't fire.
            try:
                w.chunk.disconnect()
                w.finished_ok.disconnect()
                w.failed.disconnect()
            except TypeError:
                pass
        self._worker = None

    def _position_near_cursor(self) -> None:
        """Place the popup near the cursor, kept fully inside its screen."""
        cursor_pos = QCursor.pos()
        screen = QGuiApplication.screenAt(cursor_pos) or QGuiApplication.primaryScreen()
        avail = screen.availableGeometry()

        # Initial size estimate (the body may not yet have content).
        size = self.sizeHint()
        w = max(size.width(), POPUP_WIDTH)
        h = min(max(size.height(), POPUP_MIN_HEIGHT), POPUP_MAX_HEIGHT)

        x = cursor_pos.x() + CURSOR_OFFSET.x()
        y = cursor_pos.y() + CURSOR_OFFSET.y()
        if x + w > avail.right():
            x = cursor_pos.x() - w - CURSOR_OFFSET.x()
        if y + h > avail.bottom():
            y = cursor_pos.y() - h - CURSOR_OFFSET.y()
        x = max(avail.left(), x)
        y = max(avail.top(), y)
        self.setGeometry(x, y, w, h)
