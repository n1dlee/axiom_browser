"""
AXIOM History Page — opens as a full browser tab at axiom://history.
Displays browsing history with search and clear functionality.
"""
import time
from datetime import datetime
from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt, QObject
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QLineEdit, QFrame, QSizePolicy,
)

from storage.history_manager import HistoryManager, HistoryEntry
from ui.theme import (
    BG, SURFACE_0, SURFACE_1, SURFACE_2, SURFACE_3,
    BORDER_FAINT, BORDER_MED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    ACCENT, ACCENT_BRIGHT, DANGER, FONT_FAMILY,
)

_PAGE_QSS = f"""
QWidget#history-root {{ background: {BG}; }}
QWidget#history-header {{
    background: {SURFACE_0};
    border-bottom: 1px solid {BORDER_MED};
}}

QLabel#page-title {{
    color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 700;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QLabel#date-group {{
    color: {TEXT_TERTIARY}; font-size: 10px; font-weight: 600;
    letter-spacing: 1px; font-family: {FONT_FAMILY}; background: transparent;
    padding: 2px 0px;
}}
QLabel#entry-title {{
    color: {TEXT_PRIMARY}; font-size: 13px;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QLabel#entry-url {{
    color: {ACCENT}; font-size: 11px;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QLabel#entry-time {{
    color: {TEXT_TERTIARY}; font-size: 11px;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QLabel#empty-msg {{
    color: {TEXT_TERTIARY}; font-size: 14px;
    font-family: {FONT_FAMILY}; background: transparent;
}}

/* Search input */
QLineEdit#search-input {{
    background: {SURFACE_2}; border: 1px solid {BORDER_MED};
    border-radius: 8px; color: {TEXT_PRIMARY};
    padding: 6px 14px; font-size: 13px;
    font-family: {FONT_FAMILY}; min-height: 32px;
}}
QLineEdit#search-input:focus {{ border: 1px solid {ACCENT}; }}

/* Buttons */
QPushButton#danger-btn {{
    background: transparent; border: 1px solid {DANGER};
    border-radius: 6px; color: {DANGER};
    font-size: 12px; font-family: {FONT_FAMILY};
    padding: 5px 16px; min-height: 30px;
}}
QPushButton#danger-btn:hover {{ background: rgba(255,59,92,0.10); }}

/* Entry row */
QWidget#entry-row {{
    background: transparent; border-radius: 6px;
}}
QWidget#entry-row:hover {{ background: {SURFACE_2}; }}

/* Separator */
QFrame#entry-sep {{
    background: {BORDER_FAINT}; max-height: 1px; border: none;
}}
"""


def _fmt_time(ts: float) -> str:
    dt = datetime.fromtimestamp(ts)
    return dt.strftime("%H:%M")


def _fmt_date_group(ts: float) -> str:
    dt = datetime.fromtimestamp(ts).date()
    today = datetime.now().date()
    diff = (today - dt).days
    if diff == 0:
        return "TODAY"
    elif diff == 1:
        return "YESTERDAY"
    elif diff < 7:
        return dt.strftime("%A").upper()
    else:
        return dt.strftime("%d %B %Y").upper()


class _EntryRow(QWidget):
    clicked = pyqtSignal(str)

    def __init__(self, entry: HistoryEntry, parent=None):
        super().__init__(parent)
        self.setObjectName("entry-row")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._url = entry.url
        self._build(entry)

    def _build(self, e: HistoryEntry):
        hl = QHBoxLayout(self)
        hl.setContentsMargins(12, 8, 12, 8)
        hl.setSpacing(12)

        # Text column
        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        title_lbl = QLabel(e.title or e.url)
        title_lbl.setObjectName("entry-title")
        title_lbl.setMaximumWidth(580)
        title_lbl.setWordWrap(False)
        title_lbl.setTextFormat(Qt.TextFormat.PlainText)

        url_lbl = QLabel(e.url)
        url_lbl.setObjectName("entry-url")
        url_lbl.setMaximumWidth(580)

        text_col.addWidget(title_lbl)
        text_col.addWidget(url_lbl)
        hl.addLayout(text_col, 1)

        time_lbl = QLabel(_fmt_time(e.timestamp))
        time_lbl.setObjectName("entry-time")
        time_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hl.addWidget(time_lbl)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._url)
        super().mousePressEvent(event)


class AxiomHistoryPage(QWidget):
    navigate_requested = pyqtSignal(str)

    def __init__(self, history_mgr: HistoryManager, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.setObjectName("history-root")
        self.setStyleSheet(_PAGE_QSS)
        self._history = history_mgr
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header ─────────────────────────────────────────────────
        header = QWidget()
        header.setObjectName("history-header")
        header.setFixedHeight(64)
        hdr_l = QHBoxLayout(header)
        hdr_l.setContentsMargins(32, 0, 24, 0)
        hdr_l.setSpacing(16)

        title = QLabel("History")
        title.setObjectName("page-title")
        hdr_l.addWidget(title)
        hdr_l.addStretch(1)

        self._search = QLineEdit()
        self._search.setObjectName("search-input")
        self._search.setPlaceholderText("Search history…")
        self._search.setFixedWidth(280)
        self._search.textChanged.connect(self._on_search)
        hdr_l.addWidget(self._search)

        clear_btn = QPushButton("Clear all")
        clear_btn.setObjectName("danger-btn")
        clear_btn.clicked.connect(self._on_clear)
        hdr_l.addWidget(clear_btn)

        root.addWidget(header)

        # ── Scrollable list ─────────────────────────────────────────
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
        query = self._search.text().strip()
        if query:
            entries = self._history.search(query)
        else:
            entries = self._history.get_recent(limit=200)
        self._populate(entries)

    # ── Internals ───────────────────────────────────────────────────

    def _populate(self, entries: list[HistoryEntry]) -> None:
        # Remove all widgets except the trailing stretch
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not entries:
            lbl = QLabel("No history yet." if not self._search.text() else "No matches found.")
            lbl.setObjectName("empty-msg")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._list_layout.insertWidget(0, lbl)
            return

        current_group = ""
        insert_pos = 0
        for entry in entries:
            group = _fmt_date_group(entry.timestamp)
            if group != current_group:
                current_group = group
                grp_lbl = QLabel(group)
                grp_lbl.setObjectName("date-group")
                if insert_pos > 0:
                    # add spacing before new group
                    spacer_lbl = QLabel("")
                    spacer_lbl.setFixedHeight(8)
                    spacer_lbl.setStyleSheet("background: transparent;")
                    self._list_layout.insertWidget(insert_pos, spacer_lbl)
                    insert_pos += 1
                self._list_layout.insertWidget(insert_pos, grp_lbl)
                insert_pos += 1

            row = _EntryRow(entry)
            row.clicked.connect(self.navigate_requested.emit)
            self._list_layout.insertWidget(insert_pos, row)
            insert_pos += 1

            sep = QFrame()
            sep.setObjectName("entry-sep")
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setFixedHeight(1)
            self._list_layout.insertWidget(insert_pos, sep)
            insert_pos += 1

    def _on_search(self, text: str) -> None:
        if text.strip():
            entries = self._history.search(text.strip())
        else:
            entries = self._history.get_recent(limit=200)
        self._populate(entries)

    def _on_clear(self) -> None:
        self._history.clear()
        self._populate([])
