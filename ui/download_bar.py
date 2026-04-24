"""
AXIOM Download Bar — Chrome-style download shelf at the bottom of the browser.
Appears automatically when a download starts, updates in real-time,
and provides Open / Show-in-folder actions when complete.
"""
import os
import sys
import subprocess
import time
from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt, QTimer
from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QProgressBar, QScrollArea, QSizePolicy, QFrame,
)

from ui.theme import (
    SURFACE_0, SURFACE_1, SURFACE_2, SURFACE_3,
    BORDER_MED, BORDER_FAINT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    ACCENT, ACCENT_BRIGHT, SUCCESS, DANGER, FONT_FAMILY,
)

_MAX_NAME_LEN = 22

_BAR_QSS = f"""
/* Shelf container */
QWidget#download-bar {{
    background: {SURFACE_0};
    border-top: 1px solid {BORDER_MED};
    min-height: 64px;
    max-height: 64px;
}}

/* Left "Downloads" link */
QPushButton#dl-link-btn {{
    background: transparent;
    border: none;
    color: {TEXT_SECONDARY};
    font-size: 11px;
    font-family: {FONT_FAMILY};
    padding: 0 10px;
    min-width: 80px;
    text-align: center;
}}
QPushButton#dl-link-btn:hover {{
    color: {ACCENT};
}}

/* Dismiss bar button */
QPushButton#dl-dismiss-btn {{
    background: transparent;
    border: none;
    color: {TEXT_TERTIARY};
    font-size: 14px;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
    border-radius: 6px;
}}
QPushButton#dl-dismiss-btn:hover {{
    background: {SURFACE_2};
    color: {TEXT_PRIMARY};
}}

/* ── Per-item card ─────────────────────────────────────────── */
QWidget#dl-item {{
    background: {SURFACE_1};
    border: 1px solid {BORDER_MED};
    border-radius: 8px;
}}

QLabel#dl-filename {{
    color: {TEXT_PRIMARY};
    font-size: 12px;
    font-weight: 500;
    font-family: {FONT_FAMILY};
    background: transparent;
}}
QLabel#dl-status {{
    color: {TEXT_SECONDARY};
    font-size: 10px;
    font-family: {FONT_FAMILY};
    background: transparent;
}}
QLabel#dl-done {{
    color: {SUCCESS};
    font-size: 10px;
    font-weight: 600;
    font-family: {FONT_FAMILY};
    background: transparent;
}}
QLabel#dl-fail {{
    color: {DANGER};
    font-size: 10px;
    font-weight: 600;
    font-family: {FONT_FAMILY};
    background: transparent;
}}

QProgressBar#dl-progress {{
    background: {SURFACE_2};
    border: none;
    border-radius: 2px;
    max-height: 3px;
    min-height: 3px;
    text-align: center;
}}
QProgressBar#dl-progress::chunk {{
    background: {ACCENT};
    border-radius: 2px;
}}

QPushButton#dl-action-btn {{
    background: transparent;
    border: none;
    color: {ACCENT};
    font-size: 10px;
    font-family: {FONT_FAMILY};
    padding: 0 4px;
    min-height: 18px;
}}
QPushButton#dl-action-btn:hover {{
    color: {ACCENT_BRIGHT};
    text-decoration: underline;
}}
QPushButton#dl-cancel-btn {{
    background: transparent;
    border: none;
    color: {TEXT_TERTIARY};
    font-size: 11px;
    min-width: 18px;
    max-width: 18px;
    min-height: 18px;
    max-height: 18px;
    border-radius: 4px;
}}
QPushButton#dl-cancel-btn:hover {{
    background: rgba(255,59,92,0.15);
    color: {DANGER};
}}

/* Left vertical divider before dismiss area */
QFrame#dl-vline {{
    background: {BORDER_MED};
    max-width: 1px;
    border: none;
}}
"""


def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n //= 1024
    return f"{n:.1f} GB"


def _fmt_speed(bps: float) -> str:
    return _fmt_bytes(int(bps)) + "/s"


def _open_file(path: str) -> None:
    if not os.path.exists(path):
        return
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def _show_in_folder(path: str) -> None:
    folder = os.path.dirname(path) if os.path.exists(path) else path
    if not os.path.isdir(folder):
        return
    if sys.platform == "win32":
        if os.path.exists(path):
            subprocess.Popen(["explorer", "/select,", path])
        else:
            os.startfile(folder)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-R", path])
    else:
        subprocess.Popen(["xdg-open", folder])


# ---------------------------------------------------------------------------
# Individual download item card
# ---------------------------------------------------------------------------

class _DownloadItem(QWidget):
    """A single download card inside the shelf."""

    remove_me = pyqtSignal(object)   # emits self

    _DownloadState = QWebEngineDownloadRequest.DownloadState

    def __init__(self, download: QWebEngineDownloadRequest, parent=None):
        super().__init__(parent)
        self.setObjectName("dl-item")
        self.setFixedSize(230, 52)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)

        self._dl = download
        self._save_path = os.path.join(
            download.downloadDirectory(), download.downloadFileName()
        )
        self._last_bytes: int = 0
        self._last_time: float = time.monotonic()
        self._speed: float = 0.0

        self._build()
        self._connect()

        # Speed-smoothing timer — recalculate every 800 ms
        self._speed_timer = QTimer(self)
        self._speed_timer.setInterval(800)
        self._speed_timer.timeout.connect(self._recalc_speed)
        self._speed_timer.start()

    # ── Build UI ──────────────────────────────────────────────────────

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 6, 6, 6)
        root.setSpacing(3)

        # Row 1: filename + × dismiss
        top = QHBoxLayout()
        top.setSpacing(4)

        name = self._dl.downloadFileName()
        if len(name) > _MAX_NAME_LEN:
            name = name[:_MAX_NAME_LEN - 1] + "…"
        self._name_lbl = QLabel(name)
        self._name_lbl.setObjectName("dl-filename")
        self._name_lbl.setToolTip(self._dl.downloadFileName())
        top.addWidget(self._name_lbl, 1)

        self._close_btn = QPushButton("✕")
        self._close_btn.setObjectName("dl-cancel-btn")
        self._close_btn.setToolTip("Cancel / dismiss")
        self._close_btn.clicked.connect(self._on_close)
        top.addWidget(self._close_btn)

        root.addLayout(top)

        # Row 2: progress bar (hidden once done)
        self._progress = QProgressBar()
        self._progress.setObjectName("dl-progress")
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(False)
        root.addWidget(self._progress)

        # Row 3: status + action buttons
        bot = QHBoxLayout()
        bot.setSpacing(0)
        bot.setContentsMargins(0, 0, 0, 0)

        self._status_lbl = QLabel("Starting…")
        self._status_lbl.setObjectName("dl-status")
        bot.addWidget(self._status_lbl, 1)

        # Action buttons (hidden until finished)
        self._open_btn = QPushButton("Open")
        self._open_btn.setObjectName("dl-action-btn")
        self._open_btn.hide()
        self._open_btn.clicked.connect(lambda: _open_file(self._save_path))

        self._folder_btn = QPushButton("Folder")
        self._folder_btn.setObjectName("dl-action-btn")
        self._folder_btn.hide()
        self._folder_btn.clicked.connect(lambda: _show_in_folder(self._save_path))

        bot.addWidget(self._open_btn)
        bot.addWidget(self._folder_btn)
        root.addLayout(bot)

    # ── Signals ───────────────────────────────────────────────────────

    def _connect(self) -> None:
        self._dl.receivedBytesChanged.connect(self._on_progress)
        self._dl.totalBytesChanged.connect(self._on_progress)
        self._dl.isFinishedChanged.connect(self._on_finished)

    # ── Slots ─────────────────────────────────────────────────────────

    def _on_progress(self) -> None:
        received = self._dl.receivedBytes()
        total    = self._dl.totalBytes()

        if total > 0:
            pct = int(received * 100 / total)
            self._progress.setRange(0, 100)
            self._progress.setValue(pct)
        else:
            # Unknown size — use busy indicator
            self._progress.setRange(0, 0)

        # Update status text
        if self._speed > 0:
            speed_str = f"{_fmt_speed(self._speed)}  ·  "
        else:
            speed_str = ""

        if total > 0:
            self._status_lbl.setText(
                f"{speed_str}{_fmt_bytes(received)} / {_fmt_bytes(total)}"
            )
        else:
            self._status_lbl.setText(f"{speed_str}{_fmt_bytes(received)}")

    def _recalc_speed(self) -> None:
        now = time.monotonic()
        received = self._dl.receivedBytes()
        dt = now - self._last_time
        if dt > 0 and received > self._last_bytes:
            raw_speed = (received - self._last_bytes) / dt
            # Exponential smoothing
            self._speed = self._speed * 0.4 + raw_speed * 0.6
        self._last_bytes = received
        self._last_time  = now
        self._on_progress()

    def _on_finished(self) -> None:
        self._speed_timer.stop()
        self._progress.setRange(0, 100)

        state = self._dl.state()
        if state == self._DownloadState.DownloadCompleted:
            self._progress.setValue(100)
            self._status_lbl.setObjectName("dl-done")
            self._status_lbl.setText(f"✓  {_fmt_bytes(self._dl.receivedBytes())}")
            self._status_lbl.style().unpolish(self._status_lbl)
            self._status_lbl.style().polish(self._status_lbl)
            self._close_btn.setToolTip("Dismiss")
            self._open_btn.show()
            self._folder_btn.show()

            # Auto-dismiss after 8 seconds if user hasn't interacted
            QTimer.singleShot(8_000, self._auto_dismiss)

        elif state == self._DownloadState.DownloadCancelled:
            self._progress.setValue(0)
            self._status_lbl.setObjectName("dl-fail")
            self._status_lbl.setText("Cancelled")
            self._status_lbl.style().unpolish(self._status_lbl)
            self._status_lbl.style().polish(self._status_lbl)
            QTimer.singleShot(3_000, self._auto_dismiss)

        else:  # DownloadInterrupted
            self._progress.setValue(0)
            self._status_lbl.setObjectName("dl-fail")
            self._status_lbl.setText("Failed")
            self._status_lbl.style().unpolish(self._status_lbl)
            self._status_lbl.style().polish(self._status_lbl)

    def _on_close(self) -> None:
        state = self._dl.state()
        if state == self._DownloadState.DownloadInProgress:
            self._dl.cancel()
        self.remove_me.emit(self)

    def _auto_dismiss(self) -> None:
        """Remove completed/cancelled items silently after delay."""
        self.remove_me.emit(self)


# ---------------------------------------------------------------------------
# Download shelf (the bar itself)
# ---------------------------------------------------------------------------

class AxiomDownloadBar(QWidget):
    """
    Horizontal shelf that sits at the bottom of the browser area.
    Call `add_download()` to register a QWebEngineDownloadRequest.
    The bar shows itself automatically and hides when all items are gone.
    """

    open_downloads_page = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("download-bar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(_BAR_QSS)
        self.setFixedHeight(64)
        self._items: list[_DownloadItem] = []
        self._setup_ui()
        self.hide()

    # ── Build ─────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Left "Downloads" button ──────────────────────────────
        link_btn = QPushButton("↓\nDownloads")
        link_btn.setObjectName("dl-link-btn")
        link_btn.setFixedWidth(74)
        link_btn.clicked.connect(self.open_downloads_page)
        outer.addWidget(link_btn)

        # Thin vertical divider
        vline = QFrame()
        vline.setObjectName("dl-vline")
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setFixedWidth(1)
        outer.addWidget(vline)

        # ── Scrollable item area ─────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setWidgetResizable(True)
        self._scroll.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._scroll.setFixedHeight(64)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: {SURFACE_0}; border: none; }}"
        )

        self._item_container = QWidget()
        self._item_container.setStyleSheet(f"background: {SURFACE_0};")
        self._item_layout = QHBoxLayout(self._item_container)
        self._item_layout.setContentsMargins(8, 6, 8, 6)
        self._item_layout.setSpacing(8)
        self._item_layout.addStretch(1)

        self._scroll.setWidget(self._item_container)
        outer.addWidget(self._scroll, 1)

        # ── Right dismiss all button ─────────────────────────────
        vline2 = QFrame()
        vline2.setObjectName("dl-vline")
        vline2.setFrameShape(QFrame.Shape.VLine)
        vline2.setFixedWidth(1)
        outer.addWidget(vline2)

        dismiss_btn = QPushButton("✕")
        dismiss_btn.setObjectName("dl-dismiss-btn")
        dismiss_btn.setToolTip("Hide download bar")
        dismiss_btn.setFixedWidth(38)
        dismiss_btn.clicked.connect(self._dismiss_all)
        outer.addWidget(dismiss_btn)

    # ── Public API ────────────────────────────────────────────────────

    def add_download(self, download: QWebEngineDownloadRequest) -> None:
        """Register a new download and show the bar."""
        item = _DownloadItem(download, parent=self._item_container)
        item.remove_me.connect(self._remove_item)

        # Insert before the trailing stretch
        stretch_idx = self._item_layout.count() - 1
        self._item_layout.insertWidget(stretch_idx, item)
        self._items.append(item)

        # Scroll to show the new item
        QTimer.singleShot(50, lambda: self._scroll.horizontalScrollBar().setValue(
            self._scroll.horizontalScrollBar().maximum()
        ))

        self.show()

    # ── Internals ─────────────────────────────────────────────────────

    def _remove_item(self, item: _DownloadItem) -> None:
        if item in self._items:
            self._items.remove(item)
            self._item_layout.removeWidget(item)
            item.deleteLater()

        if not self._items:
            self.hide()

    def _dismiss_all(self) -> None:
        for item in list(self._items):
            state = item._dl.state()
            if state == QWebEngineDownloadRequest.DownloadState.DownloadInProgress:
                item._dl.cancel()
        for item in list(self._items):
            self._item_layout.removeWidget(item)
            item.deleteLater()
        self._items.clear()
        self.hide()
