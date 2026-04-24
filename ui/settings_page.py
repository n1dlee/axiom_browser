"""
AXIOM Settings Page — opens as a full browser tab at axiom://settings.
Styled like Chrome's settings but in AXIOM dark-blue theme.
"""
from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt, QObject
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QLabel, QPushButton,
    QLineEdit, QCheckBox, QFrame, QScrollArea, QStackedWidget,
    QSizePolicy, QComboBox, QFileDialog, QMessageBox,
)

from core.adblock import AdBlockInterceptor
from storage.bookmarks_manager import BookmarksManager, Bookmark
from system.settings_manager import SettingsManager
from ui.newtab_page import PRESET_THEMES
from ui.theme import (
    BG, SURFACE_0, SURFACE_1, SURFACE_2, SURFACE_3,
    BORDER_FAINT, BORDER_MED, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY,
    ACCENT, ACCENT_BRIGHT, DANGER, SUCCESS, FONT_FAMILY,
)

# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------
_PAGE_QSS = f"""
QWidget#settings-root {{ background: {BG}; }}
QWidget#settings-nav  {{ background: {SURFACE_0}; border-right: 1px solid {BORDER_MED}; }}

/* Nav buttons */
QPushButton#nav-item {{
    background: transparent; border: none; border-radius: 6px;
    color: {TEXT_SECONDARY}; font-size: 13px; font-family: {FONT_FAMILY};
    text-align: left; padding: 0 16px;
    min-height: 36px; max-height: 36px;
}}
QPushButton#nav-item:hover  {{ background: {SURFACE_2}; color: {TEXT_PRIMARY}; }}
QPushButton#nav-item[active=true] {{
    background: {SURFACE_2}; color: {ACCENT};
    border-left: 2px solid {ACCENT};
}}

/* Section headings */
QLabel#section-heading {{
    color: {TEXT_PRIMARY}; font-size: 18px; font-weight: 600;
    font-family: {FONT_FAMILY}; background: transparent;
    padding-bottom: 2px;
}}
QLabel#subsection-heading {{
    color: {TEXT_SECONDARY}; font-size: 10px; font-weight: 600;
    letter-spacing: 1px; font-family: {FONT_FAMILY}; background: transparent;
    padding-top: 4px;
}}

/* Cards */
QWidget#card {{
    background: {SURFACE_1}; border-radius: 8px;
    border: 1px solid {BORDER_MED};
}}

/* Row labels */
QLabel#row-title {{
    color: {TEXT_PRIMARY}; font-size: 13px;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QLabel#row-desc {{
    color: {TEXT_SECONDARY}; font-size: 11px;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QLabel#stat-value {{
    color: {ACCENT}; font-size: 24px; font-weight: 700;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QLabel#stat-desc {{
    color: {TEXT_TERTIARY}; font-size: 11px;
    font-family: {FONT_FAMILY}; background: transparent;
}}

/* Inputs */
QLineEdit#setting-input {{
    background: {SURFACE_2}; border: 1px solid {BORDER_MED};
    border-radius: 6px; color: {TEXT_PRIMARY};
    padding: 4px 10px; font-size: 12px;
    font-family: {FONT_FAMILY}; min-height: 28px;
}}
QLineEdit#setting-input:focus {{ border: 1px solid {ACCENT}; }}

/* Combo */
QComboBox#setting-combo {{
    background: {SURFACE_2}; border: 1px solid {BORDER_MED};
    border-radius: 6px; color: {TEXT_PRIMARY};
    padding: 4px 10px; font-size: 12px;
    font-family: {FONT_FAMILY}; min-height: 28px; min-width: 180px;
}}
QComboBox#setting-combo::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background: {SURFACE_1}; border: 1px solid {BORDER_MED};
    color: {TEXT_PRIMARY}; selection-background-color: {SURFACE_3};
}}

/* Checkboxes */
QCheckBox {{
    color: {TEXT_SECONDARY}; font-size: 13px; spacing: 8px;
    font-family: {FONT_FAMILY}; background: transparent;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px; border-radius: 4px;
    border: 1px solid {BORDER_MED}; background: {SURFACE_2};
}}
QCheckBox::indicator:checked {{ background: {ACCENT}; border: 1px solid {ACCENT}; }}

/* Action buttons */
QPushButton#action-btn {{
    background: {SURFACE_2}; border: 1px solid {BORDER_MED};
    border-radius: 6px; color: {TEXT_PRIMARY};
    font-size: 12px; font-family: {FONT_FAMILY};
    padding: 5px 14px; min-height: 28px;
}}
QPushButton#action-btn:hover {{ background: {SURFACE_3}; border-color: {ACCENT}; color: {ACCENT}; }}

QPushButton#primary-btn {{
    background: {ACCENT}; border: none; border-radius: 6px;
    color: #fff; font-size: 12px; font-weight: 600;
    font-family: {FONT_FAMILY}; padding: 5px 14px; min-height: 28px;
}}
QPushButton#primary-btn:hover {{ background: {ACCENT_BRIGHT}; }}

QPushButton#danger-btn {{
    background: transparent; border: 1px solid {DANGER};
    border-radius: 6px; color: {DANGER};
    font-size: 12px; font-family: {FONT_FAMILY};
    padding: 5px 14px; min-height: 28px;
}}
QPushButton#danger-btn:hover {{ background: rgba(255,59,92,0.10); }}

/* Shortcut table */
QLabel#shortcut-key {{
    color: {ACCENT}; font-size: 11px; font-weight: 600;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    background: {SURFACE_2}; border: 1px solid {BORDER_MED};
    border-radius: 4px; padding: 2px 7px;
}}
QLabel#shortcut-desc {{
    color: {TEXT_SECONDARY}; font-size: 12px;
    font-family: {FONT_FAMILY}; background: transparent;
}}

/* Divider */
QFrame#card-divider {{
    background: {BORDER_FAINT}; max-height: 1px; border: none;
}}
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hsep() -> QFrame:
    f = QFrame()
    f.setObjectName("card-divider")
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    return f


def _scroll_wrap(widget: QWidget) -> QScrollArea:
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QScrollArea.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(widget)
    scroll.setStyleSheet(f"QScrollArea {{ background: {BG}; border: none; }}")
    return scroll


def _card(*widgets) -> QWidget:
    card = QWidget()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(20, 14, 20, 14)
    layout.setSpacing(0)
    for i, w in enumerate(widgets):
        layout.addWidget(w)
        if i < len(widgets) - 1:
            layout.addWidget(_hsep())
    return card


def _row(title: str, desc: str, control: Optional[QWidget] = None) -> QWidget:
    row = QWidget()
    row.setObjectName("card")
    row.setStyleSheet("QWidget { background: transparent; border: none; }")
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 10, 0, 10)
    hl.setSpacing(12)

    text_col = QVBoxLayout()
    text_col.setSpacing(2)
    t = QLabel(title)
    t.setObjectName("row-title")
    text_col.addWidget(t)
    if desc:
        d = QLabel(desc)
        d.setObjectName("row-desc")
        text_col.addWidget(d)
    hl.addLayout(text_col, 1)

    if control:
        hl.addWidget(control)
    return row


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

class _GeneralSection(QWidget):
    home_url_changed = pyqtSignal(str)
    restore_session_toggled = pyqtSignal(bool)
    search_engine_changed = pyqtSignal(str)

    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("General")
        heading.setObjectName("section-heading")
        layout.addWidget(heading)

        # — Search engine —
        se_lbl = QLabel("SEARCH ENGINE")
        se_lbl.setObjectName("subsection-heading")
        layout.addWidget(se_lbl)

        self._search_combo = QComboBox()
        self._search_combo.setObjectName("setting-combo")
        engines = {
            "Google":      "https://www.google.com/search?q={}",
            "DuckDuckGo":  "https://duckduckgo.com/?q={}",
            "Bing":        "https://www.bing.com/search?q={}",
            "Yandex":      "https://yandex.ru/search/?text={}",
        }
        self._engine_urls = engines
        for name in engines:
            self._search_combo.addItem(name)
        current_url = self._settings.get("search.engine_url", engines["Google"])
        for name, url in engines.items():
            if url == current_url:
                self._search_combo.setCurrentText(name)
                break
        layout.addWidget(self._search_combo)

        # — Startup —
        startup_lbl = QLabel("ON STARTUP")
        startup_lbl.setObjectName("subsection-heading")
        layout.addWidget(startup_lbl)

        self._restore_cb = QCheckBox("Restore previous session")
        self._restore_cb.setChecked(self._settings.get("startup.restore_session", True))
        layout.addWidget(self._restore_cb)

        # — Home URL —
        home_lbl = QLabel("HOME PAGE")
        home_lbl.setObjectName("subsection-heading")
        layout.addWidget(home_lbl)

        home_row = QHBoxLayout()
        home_row.setSpacing(8)
        self._home_input = QLineEdit()
        self._home_input.setObjectName("setting-input")
        self._home_input.setText(self._settings.get("startup.home_url", "https://www.google.com"))
        self._home_input.setPlaceholderText("https://www.google.com")
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primary-btn")
        save_btn.clicked.connect(self._on_save_home)
        home_row.addWidget(self._home_input, 1)
        home_row.addWidget(save_btn)
        layout.addLayout(home_row)

        layout.addStretch(1)

        # Signals
        self._search_combo.currentTextChanged.connect(
            lambda name: self.search_engine_changed.emit(self._engine_urls.get(name, ""))
        )
        self._restore_cb.toggled.connect(self.restore_session_toggled)

    def _on_save_home(self):
        url = self._home_input.text().strip()
        if url:
            self.home_url_changed.emit(url)

    def refresh(self):
        self._home_input.setText(self._settings.get("startup.home_url", "https://www.google.com"))
        self._restore_cb.setChecked(self._settings.get("startup.restore_session", True))


class _AdblockSection(QWidget):
    adblock_toggled = pyqtSignal(bool)
    count_reset = pyqtSignal()

    def __init__(self, interceptor: AdBlockInterceptor, parent=None):
        super().__init__(parent)
        self._interceptor = interceptor
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("Adblock")
        heading.setObjectName("section-heading")
        layout.addWidget(heading)

        # Toggle card
        toggle_row = _row(
            "Block ads and trackers",
            "Filters requests using a built-in domain blocklist (~500 entries).",
        )
        self._toggle_cb = QCheckBox()
        self._toggle_cb.setChecked(self._interceptor.enabled)
        toggle_row.layout().addWidget(self._toggle_cb)
        layout.addWidget(_card(toggle_row))

        # Stats card
        stats_lbl = QLabel("STATISTICS")
        stats_lbl.setObjectName("subsection-heading")
        layout.addWidget(stats_lbl)

        stats_card = QWidget()
        stats_card.setObjectName("card")
        stats_h = QHBoxLayout(stats_card)
        stats_h.setContentsMargins(20, 18, 20, 18)
        stats_h.setSpacing(24)

        # Count
        count_col = QVBoxLayout()
        self._count_lbl = QLabel(str(self._interceptor.blocked_count))
        self._count_lbl.setObjectName("stat-value")
        count_desc = QLabel("requests blocked")
        count_desc.setObjectName("stat-desc")
        count_col.addWidget(self._count_lbl)
        count_col.addWidget(count_desc)
        stats_h.addLayout(count_col)
        stats_h.addStretch(1)

        reset_btn = QPushButton("Reset counter")
        reset_btn.setObjectName("danger-btn")
        reset_btn.clicked.connect(self._on_reset)
        stats_h.addWidget(reset_btn)
        layout.addWidget(stats_card)

        layout.addStretch(1)

        self._toggle_cb.toggled.connect(self.adblock_toggled)

    def _on_reset(self):
        self._interceptor.reset_count()
        self._count_lbl.setText("0")
        self.count_reset.emit()

    def refresh(self):
        self._toggle_cb.blockSignals(True)
        self._toggle_cb.setChecked(self._interceptor.enabled)
        self._toggle_cb.blockSignals(False)
        self._count_lbl.setText(str(self._interceptor.blocked_count))


class _ThemeCard(QPushButton):
    """A clickable theme preview card showing gradient + accent colour."""

    _CARD_QSS = """
    QPushButton {{
        background: {gradient};
        border: 2px solid {border};
        border-radius: 10px;
        color: rgba(255,255,255,0.90);
        font-size: 11px; font-weight: 500;
        text-align: center;
        padding: 0;
    }}
    QPushButton:hover {{ border-color: rgba(255,255,255,0.35); }}
    """

    def __init__(self, name: str, gradient: str, accent: str, parent=None):
        super().__init__(parent)
        self._name     = name
        self._gradient = gradient
        self._accent   = accent
        self.setFixedSize(160, 64)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setText(name)
        self.setSelected(False)

    def setSelected(self, selected: bool) -> None:
        border = self._accent if selected else "rgba(255,255,255,0.10)"
        self.setStyleSheet(self._CARD_QSS.format(gradient=self._gradient, border=border))


class _AppearanceSection(QWidget):
    bookmarks_bar_toggled   = pyqtSignal(bool)
    background_path_changed = pyqtSignal(str)   # absolute path or "" to clear
    theme_preset_changed    = pyqtSignal(str)   # preset name

    def __init__(self, settings: SettingsManager, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._theme_cards: list[_ThemeCard] = []
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("Appearance")
        heading.setObjectName("section-heading")
        layout.addWidget(heading)

        # ── Bookmarks bar toggle ──────────────────────────────────────
        bm_row = _row("Show bookmarks bar", "Display pinned bookmarks below the toolbar.")
        self._bm_cb = QCheckBox()
        self._bm_cb.setChecked(self._settings.get("bookmarks_bar_visible", True))
        bm_row.layout().addWidget(self._bm_cb)
        layout.addWidget(_card(bm_row))

        # ── Theme presets ─────────────────────────────────────────────
        theme_lbl = QLabel("NEW TAB THEME")
        theme_lbl.setObjectName("subsection-heading")
        layout.addWidget(theme_lbl)

        theme_card = QWidget()
        theme_card.setObjectName("card")
        theme_v = QVBoxLayout(theme_card)
        theme_v.setContentsMargins(20, 16, 20, 16)
        theme_v.setSpacing(10)

        theme_desc = QLabel(
            "Sets the colour scheme for new tab pages. "
            "A custom background image overrides the gradient."
        )
        theme_desc.setObjectName("row-desc")
        theme_desc.setWordWrap(True)
        theme_v.addWidget(theme_desc)

        # Build grid — 3 cards per row
        grid = QGridLayout()
        grid.setSpacing(10)
        current_preset = self._settings.get("theme.preset", "Neo Noir")
        col_count = 3
        for idx, (name, props) in enumerate(PRESET_THEMES.items()):
            card = _ThemeCard(name, props["gradient"], props["accent"])
            card.setSelected(name == current_preset)
            card.clicked.connect(lambda _, n=name: self._on_preset_clicked(n))
            grid.addWidget(card, idx // col_count, idx % col_count)
            self._theme_cards.append(card)

        theme_v.addLayout(grid)
        layout.addWidget(theme_card)

        # ── New Tab background image ──────────────────────────────────
        bg_lbl = QLabel("CUSTOM BACKGROUND IMAGE")
        bg_lbl.setObjectName("subsection-heading")
        layout.addWidget(bg_lbl)

        bg_card = QWidget()
        bg_card.setObjectName("card")
        bg_v = QVBoxLayout(bg_card)
        bg_v.setContentsMargins(20, 14, 20, 14)
        bg_v.setSpacing(8)

        bg_desc = QLabel(
            "Choose an image to display on every new tab (JPG, PNG, WEBP, GIF). "
            "Overrides the theme gradient above. Leave empty to use the theme gradient."
        )
        bg_desc.setObjectName("row-desc")
        bg_desc.setWordWrap(True)
        bg_v.addWidget(bg_desc)

        current_path = self._settings.get("theme.background_path", "")
        self._bg_path_lbl = QLabel(current_path or "No image selected")
        self._bg_path_lbl.setObjectName("row-desc")
        self._bg_path_lbl.setWordWrap(True)
        bg_v.addWidget(self._bg_path_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        pick_btn = QPushButton("Choose image\u2026")
        pick_btn.setObjectName("primary-btn")
        pick_btn.setFixedWidth(150)
        pick_btn.clicked.connect(self._pick_background)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("danger-btn")
        clear_btn.setFixedWidth(80)
        clear_btn.clicked.connect(self._clear_background)

        btn_row.addWidget(pick_btn)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch(1)
        bg_v.addLayout(btn_row)
        layout.addWidget(bg_card)

        layout.addStretch(1)

        self._bm_cb.toggled.connect(self.bookmarks_bar_toggled)

    def _on_preset_clicked(self, name: str) -> None:
        for card in self._theme_cards:
            card.setSelected(card._name == name)
        self.theme_preset_changed.emit(name)

    def _pick_background(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choose background image", "",
            "Images (*.png *.jpg *.jpeg *.webp *.gif);;All Files (*)"
        )
        if path:
            self._bg_path_lbl.setText(path)
            self.background_path_changed.emit(path)

    def _clear_background(self):
        self._bg_path_lbl.setText("No image selected")
        self.background_path_changed.emit("")

    def refresh(self, bookmarks_visible: bool):
        self._bm_cb.blockSignals(True)
        self._bm_cb.setChecked(bookmarks_visible)
        self._bm_cb.blockSignals(False)
        current = self._settings.get("theme.background_path", "")
        self._bg_path_lbl.setText(current or "No image selected")
        current_preset = self._settings.get("theme.preset", "Neo Noir")
        for card in self._theme_cards:
            card.setSelected(card._name == current_preset)


class _BookmarksSection(QWidget):
    bookmarks_imported = pyqtSignal(list)   # emits list[Bookmark] after any import

    def __init__(self, bookmarks_mgr: BookmarksManager, parent=None):
        super().__init__(parent)
        self._mgr = bookmarks_mgr
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("Bookmarks")
        heading.setObjectName("section-heading")
        layout.addWidget(heading)

        # ── Import from Chrome ────────────────────────────────────────
        chrome_lbl = QLabel("IMPORT FROM CHROME")
        chrome_lbl.setObjectName("subsection-heading")
        layout.addWidget(chrome_lbl)

        chrome_card = QWidget()
        chrome_card.setObjectName("card")
        chrome_v = QVBoxLayout(chrome_card)
        chrome_v.setContentsMargins(20, 14, 20, 14)
        chrome_v.setSpacing(8)

        chrome_desc = QLabel(
            "Reads Chrome's local bookmarks file directly — no login required.\n"
            "Duplicates are skipped automatically."
        )
        chrome_desc.setObjectName("row-desc")
        chrome_desc.setWordWrap(True)
        chrome_v.addWidget(chrome_desc)

        self._chrome_status = QLabel("")
        self._chrome_status.setObjectName("row-desc")
        self._chrome_status.setWordWrap(True)
        chrome_v.addWidget(self._chrome_status)

        chrome_btn = QPushButton("Import from Chrome")
        chrome_btn.setObjectName("primary-btn")
        chrome_btn.setFixedWidth(180)
        chrome_btn.clicked.connect(self._on_import_chrome)
        chrome_v.addWidget(chrome_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(chrome_card)

        # ── Import from HTML ──────────────────────────────────────────
        html_lbl = QLabel("IMPORT FROM HTML FILE")
        html_lbl.setObjectName("subsection-heading")
        layout.addWidget(html_lbl)

        html_card = QWidget()
        html_card.setObjectName("card")
        html_v = QVBoxLayout(html_card)
        html_v.setContentsMargins(20, 14, 20, 14)
        html_v.setSpacing(8)

        html_desc = QLabel(
            "Supports the standard Netscape Bookmark Format exported by\n"
            "Chrome, Firefox, Edge, and Safari."
        )
        html_desc.setObjectName("row-desc")
        html_desc.setWordWrap(True)
        html_v.addWidget(html_desc)

        self._html_status = QLabel("")
        self._html_status.setObjectName("row-desc")
        self._html_status.setWordWrap(True)
        html_v.addWidget(self._html_status)

        html_btn = QPushButton("Choose HTML file…")
        html_btn.setObjectName("action-btn")
        html_btn.setFixedWidth(180)
        html_btn.clicked.connect(self._on_import_html)
        html_v.addWidget(html_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(html_card)

        # ── Export to HTML ────────────────────────────────────────────
        export_lbl = QLabel("EXPORT")
        export_lbl.setObjectName("subsection-heading")
        layout.addWidget(export_lbl)

        export_card = QWidget()
        export_card.setObjectName("card")
        export_v = QVBoxLayout(export_card)
        export_v.setContentsMargins(20, 14, 20, 14)
        export_v.setSpacing(8)

        export_desc = QLabel(
            "Save all AXIOM bookmarks as an HTML file that any browser can import."
        )
        export_desc.setObjectName("row-desc")
        export_desc.setWordWrap(True)
        export_v.addWidget(export_desc)

        self._export_status = QLabel("")
        self._export_status.setObjectName("row-desc")
        self._export_status.setWordWrap(True)
        export_v.addWidget(self._export_status)

        export_btn = QPushButton("Export bookmarks…")
        export_btn.setObjectName("action-btn")
        export_btn.setFixedWidth(180)
        export_btn.clicked.connect(self._on_export_html)
        export_v.addWidget(export_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        layout.addWidget(export_card)
        layout.addStretch(1)

    # ── Slots ──────────────────────────────────────────────────────────

    def _on_import_chrome(self):
        self._chrome_status.setText("")
        try:
            added = self._mgr.import_from_chrome()
            if added:
                self._chrome_status.setStyleSheet(f"color: #32D74B;")
                self._chrome_status.setText(f"✓ Imported {len(added)} new bookmarks from Chrome.")
                self.bookmarks_imported.emit(added)
            else:
                self._chrome_status.setStyleSheet(f"color: {TEXT_SECONDARY};")
                self._chrome_status.setText("No new bookmarks found — all already exist in AXIOM.")
        except FileNotFoundError as exc:
            self._chrome_status.setStyleSheet(f"color: #FF453A;")
            self._chrome_status.setText(str(exc))
        except Exception as exc:
            self._chrome_status.setStyleSheet(f"color: #FF453A;")
            self._chrome_status.setText(f"Error: {exc}")

    def _on_import_html(self):
        self._html_status.setText("")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Bookmarks HTML", "",
            "HTML Bookmark Files (*.html *.htm);;All Files (*)"
        )
        if not path:
            return
        try:
            added = self._mgr.import_from_html(path)
            if added:
                self._html_status.setStyleSheet(f"color: #32D74B;")
                self._html_status.setText(f"✓ Imported {len(added)} new bookmarks.")
                self.bookmarks_imported.emit(added)
            else:
                self._html_status.setStyleSheet(f"color: {TEXT_SECONDARY};")
                self._html_status.setText("No new bookmarks found — all already exist in AXIOM.")
        except Exception as exc:
            self._html_status.setStyleSheet(f"color: #FF453A;")
            self._html_status.setText(f"Error reading file: {exc}")

    def _on_export_html(self):
        self._export_status.setText("")
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Bookmarks", "axiom_bookmarks.html",
            "HTML Files (*.html);;All Files (*)"
        )
        if not path:
            return
        try:
            count = self._mgr.export_to_html(path)
            self._export_status.setStyleSheet(f"color: #32D74B;")
            self._export_status.setText(f"✓ Exported {count} bookmarks to {path}")
        except Exception as exc:
            self._export_status.setStyleSheet(f"color: #FF453A;")
            self._export_status.setText(f"Error: {exc}")


class _ShortcutsSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("Keyboard Shortcuts")
        heading.setObjectName("section-heading")
        layout.addWidget(heading)

        shortcuts = [
            ("Ctrl+T",        "Open new tab"),
            ("Ctrl+W",        "Close current tab"),
            ("Ctrl+D",        "Bookmark current page"),
            ("Ctrl+Shift+B",  "Show / hide bookmarks bar"),
            ("F5",            "Reload page"),
            ("F12",           "Toggle Developer Tools"),
            ("Alt+Left",      "Go back"),
            ("Alt+Right",     "Go forward"),
            ("axiom://settings", "Open settings"),
        ]

        rows = []
        for key, desc in shortcuts:
            row = QWidget()
            row.setStyleSheet("background: transparent; border: none;")
            hl = QHBoxLayout(row)
            hl.setContentsMargins(0, 10, 0, 10)
            key_lbl = QLabel(key)
            key_lbl.setObjectName("shortcut-key")
            key_lbl.setFixedWidth(200)
            desc_lbl = QLabel(desc)
            desc_lbl.setObjectName("shortcut-desc")
            hl.addWidget(key_lbl)
            hl.addWidget(desc_lbl, 1)
            rows.append(row)

        layout.addWidget(_card(*rows))
        layout.addStretch(1)


class _AboutSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        heading = QLabel("About AXIOM")
        heading.setObjectName("section-heading")
        layout.addWidget(heading)

        about_card = QWidget()
        about_card.setObjectName("card")
        ac_layout = QVBoxLayout(about_card)
        ac_layout.setContentsMargins(20, 18, 20, 18)
        ac_layout.setSpacing(8)

        for label, value in [
            ("Version",  "1.0.0"),
            ("Engine",   "Chromium via Qt WebEngine"),
            ("Runtime",  "PyQt6"),
            ("Theme",    "Neo-Future Dark"),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setObjectName("row-title")
            lbl.setFixedWidth(100)
            val = QLabel(value)
            val.setObjectName("row-desc")
            row.addWidget(lbl)
            row.addWidget(val, 1)
            ac_layout.addLayout(row)

        layout.addWidget(about_card)
        layout.addStretch(1)


# ---------------------------------------------------------------------------
# Main settings page
# ---------------------------------------------------------------------------

class AxiomSettingsPage(QWidget):
    # Signals that main_window listens to
    home_url_changed           = pyqtSignal(str)
    search_engine_changed      = pyqtSignal(str)
    adblock_toggled            = pyqtSignal(bool)
    restore_session_toggled    = pyqtSignal(bool)
    bookmarks_bar_toggled      = pyqtSignal(bool)
    bookmarks_imported         = pyqtSignal(list)   # list[Bookmark]
    background_path_changed    = pyqtSignal(str)    # new tab background image path
    theme_preset_changed       = pyqtSignal(str)    # preset name

    def __init__(
        self,
        interceptor: AdBlockInterceptor,
        settings_mgr: SettingsManager,
        bookmarks_mgr: Optional[BookmarksManager] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("settings-root")
        self.setStyleSheet(_PAGE_QSS)
        self._interceptor = interceptor
        self._settings = settings_mgr
        self._bookmarks_mgr = bookmarks_mgr
        self._nav_btns: list[QPushButton] = []
        self._setup_ui()

    def _setup_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left nav (220px) ──────────────────────────────────────
        nav_widget = QWidget()
        nav_widget.setObjectName("settings-nav")
        nav_widget.setFixedWidth(220)
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(12, 24, 12, 16)
        nav_layout.setSpacing(2)

        title = QLabel("Settings")
        title.setStyleSheet(
            f"color: {TEXT_PRIMARY}; font-size: 20px; font-weight: 700;"
            f" font-family: {FONT_FAMILY}; background: transparent;"
            f" padding: 0 4px 16px 4px;"
        )
        nav_layout.addWidget(title)

        sections = ["General", "Adblock", "Appearance", "Bookmarks", "Shortcuts", "About"]
        for i, name in enumerate(sections):
            btn = QPushButton(name)
            btn.setObjectName("nav-item")
            btn.setCheckable(False)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.setFixedHeight(36)
            idx = i
            btn.clicked.connect(lambda _, n=idx: self._switch(n))
            nav_layout.addWidget(btn)
            self._nav_btns.append(btn)

        nav_layout.addStretch(1)
        root.addWidget(nav_widget)

        # Vertical divider
        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setFixedWidth(1)
        vline.setStyleSheet(f"background: {BORDER_MED}; border: none;")
        root.addWidget(vline)

        # ── Right content stack ───────────────────────────────────
        self._general    = _GeneralSection(self._settings)
        self._adblock_s  = _AdblockSection(self._interceptor)
        self._appearance = _AppearanceSection(self._settings)
        self._bm_section = _BookmarksSection(self._bookmarks_mgr) if self._bookmarks_mgr else QWidget()
        self._shortcuts  = _ShortcutsSection()
        self._about      = _AboutSection()

        self._stack = QStackedWidget()
        for section in (
            self._general, self._adblock_s, self._appearance,
            self._bm_section, self._shortcuts, self._about
        ):
            self._stack.addWidget(_scroll_wrap(section))

        root.addWidget(self._stack, 1)

        # Wire section signals → page signals
        self._general.home_url_changed.connect(self.home_url_changed)
        self._general.search_engine_changed.connect(self.search_engine_changed)
        self._general.restore_session_toggled.connect(self.restore_session_toggled)
        self._adblock_s.adblock_toggled.connect(self.adblock_toggled)
        self._appearance.bookmarks_bar_toggled.connect(self.bookmarks_bar_toggled)
        self._appearance.background_path_changed.connect(self.background_path_changed)
        self._appearance.theme_preset_changed.connect(self.theme_preset_changed)
        if isinstance(self._bm_section, _BookmarksSection):
            self._bm_section.bookmarks_imported.connect(self.bookmarks_imported)

        self._switch(0)

    def _switch(self, index: int) -> None:
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_btns):
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def refresh(self, bookmarks_visible: bool) -> None:
        """Call when the tab becomes active to sync live values."""
        self._general.refresh()
        self._adblock_s.refresh()
        self._appearance.refresh(bookmarks_visible)
