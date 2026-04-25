"""
AXIOM History Page — opens as a full browser tab at axiom://history.
Displays browsing history with search, per-entry delete, and domain delete.
"""
import time
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from PyQt6.QtCore import pyqtSignal, Qt, QObject
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QLineEdit, QFrame, QMenu, QSizePolicy,
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

/* Domain-filter chip */
QPushButton#domain-chip {{
    background: rgba(91,156,246,0.12); border: 1px solid {ACCENT};
    border-radius: 14px; color: {ACCENT};
    font-size: 11px; font-family: {FONT_FAMILY};
    padding: 3px 10px 3px 12px; min-height: 26px;
}}
QPushButton#domain-chip:hover {{ background: rgba(91,156,246,0.22); }}

/* Entry row */
QWidget#entry-row {{
    background: transparent; border-radius: 6px;
}}
QWidget#entry-row:hover {{ background: {SURFACE_2}; }}

/* Context menu */
QMenu {{
    background: #111120;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 4px;
    color: {TEXT_PRIMARY};
    font-size: 12px;
    font-family: {FONT_FAMILY};
}}
QMenu::item {{
    padding: 7px 22px 7px 12px;
    border-radius: 4px;
    background: transparent;
}}
QMenu::item:selected {{ background: #20203A; color: {ACCENT}; }}
QMenu::item:disabled {{ color: rgba(242,242,242,0.30); }}
QMenu::separator {{ height: 1px; background: rgba(255,255,255,0.07); margin: 3px 8px; }}

/* Separator */
QFrame#entry-sep {{
    background: {BORDER_FAINT}; max-height: 1px; border: none;
}}
"""

_MENU_QSS = """
QMenu {
    background: #111120;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 4px;
    color: #F2F2F2;
    font-size: 12px;
}
QMenu::item {
    padding: 7px 22px 7px 12px;
    border-radius: 4px;
    background: transparent;
}
QMenu::item:selected { background: #20203A; color: #5B9CF6; }
QMenu::separator { height: 1px; background: rgba(255,255,255,0.07); margin: 3px 8px; }
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


def _domain_from_url(url: str) -> str:
    """Extract the registrable host (netloc) from a URL, or '' on failure."""
    try:
        return urlparse(url).netloc or ""
    except Exception:
        return ""


class _EntryRow(QWidget):
    clicked         = pyqtSignal(str)          # url
    delete_requested = pyqtSignal(int)          # entry id
    delete_domain_requested = pyqtSignal(str)  # domain string
    filter_domain_requested = pyqtSignal(str)  # domain string

    def __init__(self, entry: HistoryEntry, parent=None):
        super().__init__(parent)
        self.setObjectName("entry-row")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._url = entry.url
        self._entry_id = entry.id
        self._domain = _domain_from_url(entry.url)
        self._build(entry)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _build(self, e: HistoryEntry):
        hl = QHBoxLayout(self)
        hl.setContentsMargins(12, 8, 12, 8)
        hl.setSpacing(12)

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

    def _show_context_menu(self, pos) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(_MENU_QSS)

        open_act   = menu.addAction("Open")
        menu.addSeparator()
        del_act    = menu.addAction("Delete this entry")
        if self._domain:
            domain_del_act    = menu.addAction(f"Delete all from  {self._domain}")
            domain_filter_act = menu.addAction(f"Show only  {self._domain}")
        else:
            domain_del_act    = None
            domain_filter_act = None

        chosen = menu.exec(self.mapToGlobal(pos))
        if chosen is None:
            return
        if chosen == open_act:
            self.clicked.emit(self._url)
        elif chosen == del_act:
            self.delete_requested.emit(self._entry_id)
        elif domain_del_act and chosen == domain_del_act:
            self.delete_domain_requested.emit(self._domain)
        elif domain_filter_act and chosen == domain_filter_act:
            self.filter_domain_requested.emit(self._domain)


class AxiomHistoryPage(QWidget):
    navigate_requested = pyqtSignal(str)

    def __init__(self, history_mgr: HistoryManager, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.setObjectName("history-root")
        self.setStyleSheet(_PAGE_QSS)
        self._history = history_mgr
        self._domain_filter: str = ""   # "" = no filter
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
        hdr_l.setSpacing(12)

        title = QLabel("History")
        title.setObjectName("page-title")
        hdr_l.addWidget(title)

        # Domain filter chip — hidden until user triggers domain filter
        self._domain_chip = QPushButton()
        self._domain_chip.setObjectName("domain-chip")
        self._domain_chip.setVisible(False)
        self._domain_chip.clicked.connect(self._clear_domain_filter)
        hdr_l.addWidget(self._domain_chip)

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
        entries = self._load_entries(query)
        self._populate(entries)

    # ── Internals ───────────────────────────────────────────────────

    def _load_entries(self, query: str) -> list[HistoryEntry]:
        """Fetch entries from storage, applying text search and domain filter."""
        if query:
            entries = self._history.search(query)
        else:
            entries = self._history.get_recent(limit=500)

        if self._domain_filter:
            entries = [e for e in entries if self._domain_filter in _domain_from_url(e.url)]
        return entries

    def _populate(self, entries: list[HistoryEntry]) -> None:
        # Remove all widgets except the trailing stretch
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not entries:
            msg = "No history yet." if not self._search.text() and not self._domain_filter \
                else "No matches found."
            lbl = QLabel(msg)
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
                    spacer_lbl = QLabel("")
                    spacer_lbl.setFixedHeight(8)
                    spacer_lbl.setStyleSheet("background: transparent;")
                    self._list_layout.insertWidget(insert_pos, spacer_lbl)
                    insert_pos += 1
                self._list_layout.insertWidget(insert_pos, grp_lbl)
                insert_pos += 1

            row = _EntryRow(entry)
            row.clicked.connect(self.navigate_requested.emit)
            row.delete_requested.connect(self._on_delete_entry)
            row.delete_domain_requested.connect(self._on_delete_domain)
            row.filter_domain_requested.connect(self._on_filter_domain)
            self._list_layout.insertWidget(insert_pos, row)
            insert_pos += 1

            sep = QFrame()
            sep.setObjectName("entry-sep")
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setFixedHeight(1)
            self._list_layout.insertWidget(insert_pos, sep)
            insert_pos += 1

    def _on_search(self, text: str) -> None:
        self._populate(self._load_entries(text.strip()))

    def _on_clear(self) -> None:
        self._history.clear()
        self._domain_filter = ""
        self._domain_chip.setVisible(False)
        self._populate([])

    def _on_delete_entry(self, entry_id: int) -> None:
        """Delete one entry and refresh without losing scroll position or search."""
        self._history.delete_entry(entry_id)
        self.refresh()

    def _on_delete_domain(self, domain: str) -> None:
        """Delete all entries for a domain and refresh."""
        self._history.delete_by_domain(domain)
        # If we were filtering that domain, clear the filter too
        if self._domain_filter == domain:
            self._clear_domain_filter()
        else:
            self.refresh()

    def _on_filter_domain(self, domain: str) -> None:
        """Narrow the list to a single domain and show the active chip."""
        self._domain_filter = domain
        self._domain_chip.setText(f"  {domain}  ✕")
        self._domain_chip.setVisible(True)
        self.refresh()

    def _clear_domain_filter(self) -> None:
        self._domain_filter = ""
        self._domain_chip.setVisible(False)
        self.refresh()
