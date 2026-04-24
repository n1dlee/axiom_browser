"""
AXIOM Downloads Page — opens as a full browser tab at axiom://downloads.
Displays download history with status indicators and file-open shortcuts.
"""
import os
import subprocess
import sys
from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt, QObject
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSizePolicy,
)

from storage.downloads_manager import DownloadsManager, DownloadEntry, DownloadStatus
from ui.theme import (
    BG, SURFACE_0, SURFACE_1, SURFACE_2,
    BORDER_FAINT, BORDER_MED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    ACCENT, ACCENT_BRIGHT, DANGER, SUCCESS, FONT_FAMILY,
)

_STATUS_COLORS = {
    DownloadStatus.COMPLETED:   SUCCESS,
    DownloadStatus.IN_PROGRESS: ACCENT,
    DownloadStatus.PENDING:     TEXT_TERTIARY,
    DownloadStatus.FAILED:      DANGER,
    DownloadStatus.CANCELLED:   TEXT_TERTIARY,
}
_STATUS_LABELS = {
    DownloadStatus.COMPLETED:   "Completed",
    DownloadStatus.IN_PROGRESS: "In progress",
    DownloadStatus.PENDING:     "Pending",
    DownloadStatus.FAILED:      "Failed",
    DownloadStatus.CANCELLED:   "Cancelled",
}

_PAGE_QSS = f"""
QWidget#downloads-root {{ background: {BG}; }}
QWidget#dl-header {{
    background: {SURFACE_0};
    border-bottom: 1px solid {BORDER_MED};
}}
QLabel#page-title {{
    color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 700;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QLabel#dl-filename {{
    color: {TEXT_PRIMARY}; font-size: 13px; font-weight: 500;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QLabel#dl-source {{
    color: {TEXT_TERTIARY}; font-size: 11px;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QLabel#dl-meta {{
    color: {TEXT_SECONDARY}; font-size: 11px;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QLabel#empty-msg {{
    color: {TEXT_TERTIARY}; font-size: 14px;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QPushButton#danger-btn {{
    background: transparent; border: 1px solid {DANGER};
    border-radius: 6px; color: {DANGER};
    font-size: 12px; font-family: {FONT_FAMILY};
    padding: 5px 16px; min-height: 30px;
}}
QPushButton#danger-btn:hover {{ background: rgba(255,59,92,0.10); }}
QPushButton#open-btn {{
    background: {SURFACE_2}; border: 1px solid {BORDER_MED};
    border-radius: 5px; color: {TEXT_SECONDARY};
    font-size: 11px; font-family: {FONT_FAMILY};
    padding: 3px 10px; min-height: 24px;
}}
QPushButton#open-btn:hover {{
    background: {SURFACE_1}; border-color: {ACCENT}; color: {ACCENT};
}}
QFrame#entry-sep {{
    background: {BORDER_FAINT}; max-height: 1px; border: none;
}}
"""


def _fmt_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.0f} {unit}"
        size_bytes /= 1024  # type: ignore[assignment]
    return f"{size_bytes:.1f} TB"


def _fmt_ts(ts: float) -> str:
    from datetime import datetime
    return datetime.fromtimestamp(ts).strftime("%d %b %Y, %H:%M")


def _open_path(path: str) -> None:
    """Open a file or its containing folder."""
    if not os.path.exists(path):
        # Try opening the folder
        folder = os.path.dirname(path)
        if os.path.isdir(folder):
            path = folder
        else:
            return
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


def _show_in_folder(path: str) -> None:
    folder = os.path.dirname(path)
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


class _DownloadRow(QWidget):
    def __init__(self, entry: DownloadEntry, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._build()

    def _build(self) -> None:
        e = self._entry
        hl = QHBoxLayout(self)
        hl.setContentsMargins(12, 12, 12, 12)
        hl.setSpacing(12)

        # Left: icon placeholder — colored status dot
        dot = QLabel("●")
        color = _STATUS_COLORS.get(e.status, TEXT_TERTIARY)
        dot.setStyleSheet(
            f"color: {color}; font-size: 10px; background: transparent;"
            f" font-family: {FONT_FAMILY};"
        )
        dot.setFixedWidth(16)
        dot.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        hl.addWidget(dot)

        # Center: text stack
        text_col = QVBoxLayout()
        text_col.setSpacing(3)

        name_lbl = QLabel(e.filename)
        name_lbl.setObjectName("dl-filename")

        meta_parts = []
        if e.size_bytes:
            meta_parts.append(_fmt_size(e.size_bytes))
        meta_parts.append(_STATUS_LABELS.get(e.status, e.status.value))
        meta_parts.append(_fmt_ts(e.timestamp))

        meta_lbl = QLabel("  ·  ".join(meta_parts))
        meta_lbl.setObjectName("dl-meta")

        src_lbl = QLabel(e.source_url)
        src_lbl.setObjectName("dl-source")
        src_lbl.setMaximumWidth(500)

        text_col.addWidget(name_lbl)
        text_col.addWidget(meta_lbl)
        text_col.addWidget(src_lbl)
        hl.addLayout(text_col, 1)

        # Right: action buttons
        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)
        btn_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        if e.status == DownloadStatus.COMPLETED and os.path.exists(e.save_path):
            open_btn = QPushButton("Open file")
            open_btn.setObjectName("open-btn")
            open_btn.clicked.connect(lambda: _open_path(e.save_path))
            btn_col.addWidget(open_btn)

        folder_btn = QPushButton("Show in folder")
        folder_btn.setObjectName("open-btn")
        folder_btn.clicked.connect(lambda: _show_in_folder(e.save_path))
        btn_col.addWidget(folder_btn)

        hl.addLayout(btn_col)


class AxiomDownloadsPage(QWidget):
    def __init__(self, downloads_mgr: DownloadsManager, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.setObjectName("downloads-root")
        self.setStyleSheet(_PAGE_QSS)
        self._downloads = downloads_mgr
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("dl-header")
        header.setFixedHeight(64)
        hdr_l = QHBoxLayout(header)
        hdr_l.setContentsMargins(32, 0, 24, 0)

        title = QLabel("Downloads")
        title.setObjectName("page-title")
        hdr_l.addWidget(title)
        hdr_l.addStretch(1)

        clear_btn = QPushButton("Clear list")
        clear_btn.setObjectName("danger-btn")
        clear_btn.clicked.connect(self._on_clear)
        hdr_l.addWidget(clear_btn)

        root.addWidget(header)

        # ── List ────────────────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(f"QScrollArea {{ background: {BG}; border: none; }}")

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet(f"background: {BG};")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(32, 16, 32, 32)
        self._list_layout.setSpacing(0)
        self._list_layout.addStretch(1)

        self._scroll.setWidget(self._list_widget)
        root.addWidget(self._scroll, 1)

    # ── Public ──────────────────────────────────────────────────────

    def refresh(self) -> None:
        entries = self._downloads.get_all()
        self._populate(entries)

    # ── Internals ───────────────────────────────────────────────────

    def _populate(self, entries: list[DownloadEntry]) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not entries:
            lbl = QLabel("No downloads yet.")
            lbl.setObjectName("empty-msg")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.insertWidget(0, lbl)
            return

        for i, entry in enumerate(entries):
            row = _DownloadRow(entry)
            self._list_layout.insertWidget(i * 2, row)
            if i < len(entries) - 1:
                sep = QFrame()
                sep.setObjectName("entry-sep")
                sep.setFrameShape(QFrame.Shape.HLine)
                sep.setFixedHeight(1)
                self._list_layout.insertWidget(i * 2 + 1, sep)

    def _on_clear(self) -> None:
        # DownloadsManager doesn't have a clear() yet — add inline
        if self._downloads._conn:
            self._downloads._conn.execute("DELETE FROM downloads")
            self._downloads._conn.commit()
        self._populate([])
