# AXIOM Design System — Neo-Future × Apple Precision

# ---------------------------------------------------------------------------
# Color tokens
# ---------------------------------------------------------------------------

BG              = "#09090F"        # void black
SURFACE_0       = "#0E0E18"        # sidebar + tab strip
SURFACE_1       = "#111120"        # toolbar
SURFACE_2       = "#181830"        # inputs / inactive hover
SURFACE_3       = "#20203A"        # hover + pressed states
SURFACE_ACTIVE  = "#1C1C34"        # active tab / active sidebar item

BORDER_FAINT    = "rgba(100,120,255,0.09)"
BORDER_MED      = "rgba(100,120,255,0.20)"
BORDER_STRONG   = "rgba(100,120,255,0.38)"
SEPARATOR       = "rgba(100,120,255,0.07)"

TEXT_PRIMARY    = "#ECEEFF"
TEXT_SECONDARY  = "rgba(180,195,255,0.60)"
TEXT_TERTIARY   = "rgba(140,160,255,0.32)"

ACCENT          = "#4F8EFF"        # electric indigo-blue
ACCENT_BRIGHT   = "#7AABFF"        # lighter variant for glow hints
ACCENT_DIM      = "rgba(79,142,255,0.14)"
ACCENT_GLOW     = "rgba(79,142,255,0.28)"

SUCCESS         = "#1FD17A"        # neon green (adblock on)
DANGER          = "#FF3B5C"        # neon red (close / destructive)

# ---------------------------------------------------------------------------
# Typography
# ---------------------------------------------------------------------------

FONT_FAMILY = "'Segoe UI Variable', 'Segoe UI', -apple-system, sans-serif"
FONT_MONO   = "'Cascadia Code', 'Consolas', monospace"


# ---------------------------------------------------------------------------
# Global QSS
# ---------------------------------------------------------------------------

def build_global_qss() -> str:
    return f"""
/* ── Root ────────────────────────────────────────────────────────────────── */
QMainWindow {{
    background: {BG};
}}
QWidget {{
    font-family: {FONT_FAMILY};
    color: {TEXT_PRIMARY};
    background: transparent;
    border: none;
    outline: none;
}}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
QWidget#sidebar {{
    background: {SURFACE_0};
    border-right: 1px solid {BORDER_MED};
    min-width: 46px;
    max-width: 46px;
}}

/* Sidebar brand mark */
QLabel#sidebar-brand {{
    color: {ACCENT};
    font-size: 15px;
    font-weight: 700;
    background: transparent;
}}

/* Sidebar separator line */
QFrame#sidebar-sep {{
    background: {BORDER_MED};
    max-height: 1px;
    border: none;
}}

/* Sidebar icon buttons */
QPushButton#sidebar-btn {{
    background: transparent;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0px;
    color: {TEXT_SECONDARY};
    font-size: 16px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
    padding: 0px;
    margin: 0px;
}}
QPushButton#sidebar-btn:hover {{
    background: {SURFACE_2};
    color: {TEXT_PRIMARY};
    border-left: 2px solid {ACCENT_GLOW};
}}
QPushButton#sidebar-btn:pressed {{
    background: {SURFACE_3};
    color: {ACCENT};
    border-left: 2px solid {ACCENT};
}}
QPushButton#sidebar-btn[active=true] {{
    background: {SURFACE_ACTIVE};
    color: {ACCENT_BRIGHT};
    border-left: 2px solid {ACCENT};
}}

/* ── Tab strip ───────────────────────────────────────────────────────────── */
QWidget#tab-strip {{
    background: {SURFACE_0};
    min-height: 40px;
    max-height: 40px;
    border-bottom: 1px solid {BORDER_MED};
}}
QTabBar {{
    background: transparent;
    border: none;
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_SECONDARY};
    padding: 0px 16px;
    min-width: 100px;
    max-width: 220px;
    min-height: 38px;
    max-height: 38px;
    font-size: 12px;
    font-family: {FONT_FAMILY};
    border: none;
    border-bottom: 2px solid transparent;
    margin-right: 1px;
}}
QTabBar::tab:selected {{
    background: {SURFACE_ACTIVE};
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {ACCENT};
    font-weight: 500;
}}
QTabBar::tab:hover:!selected {{
    background: {SURFACE_2};
    color: rgba(200,215,255,0.88);
    border-bottom: 2px solid {BORDER_STRONG};
}}
QTabBar::close-button {{
    subcontrol-position: right;
    width: 12px;
    height: 12px;
    margin-right: 3px;
    border-radius: 6px;
}}
QTabBar::close-button:hover {{
    background: rgba(255,59,92,0.22);
}}

/* ── New-tab button ──────────────────────────────────────────────────────── */
QPushButton#new-tab-btn {{
    background: transparent;
    border: none;
    border-radius: 6px;
    color: {TEXT_SECONDARY};
    font-size: 17px;
    font-weight: 300;
    min-width: 28px;
    max-width: 28px;
    min-height: 28px;
    max-height: 28px;
}}
QPushButton#new-tab-btn:hover {{
    background: {SURFACE_3};
    color: {ACCENT};
}}
QPushButton#new-tab-btn:pressed {{
    background: {SURFACE_ACTIVE};
}}

/* ── Toolbar ─────────────────────────────────────────────────────────────── */
QWidget#toolbar {{
    background: {SURFACE_1};
    min-height: 46px;
    max-height: 46px;
    border-bottom: 1px solid {BORDER_MED};
}}

/* Nav buttons */
QPushButton#nav-btn {{
    background: transparent;
    border: none;
    border-radius: 7px;
    color: {TEXT_SECONDARY};
    font-size: 15px;
    min-width: 32px;
    max-width: 32px;
    min-height: 32px;
    max-height: 32px;
}}
QPushButton#nav-btn:hover {{
    background: {SURFACE_3};
    color: {TEXT_PRIMARY};
}}
QPushButton#nav-btn:pressed {{
    background: {SURFACE_ACTIVE};
    color: {ACCENT};
}}
QPushButton#nav-btn:disabled {{
    color: {TEXT_TERTIARY};
}}

/* Omnibox */
QLineEdit#omnibox {{
    background: {SURFACE_2};
    border: 1px solid {BORDER_MED};
    border-radius: 8px;
    color: {TEXT_PRIMARY};
    padding: 0px 14px;
    font-size: 13px;
    font-family: {FONT_FAMILY};
    min-height: 32px;
    max-height: 32px;
    selection-background-color: {ACCENT_DIM};
    selection-color: {TEXT_PRIMARY};
}}
QLineEdit#omnibox:focus {{
    border: 1px solid {ACCENT};
    background: {SURFACE_3};
}}

/* ── Bookmarks bar ───────────────────────────────────────────────────────── */
QWidget#bookmarks-bar {{
    background: {SURFACE_0};
    min-height: 30px;
    max-height: 30px;
    border-bottom: 1px solid {BORDER_FAINT};
}}
QPushButton#bookmark-chip {{
    background: transparent;
    border: none;
    border-radius: 5px;
    color: {TEXT_SECONDARY};
    font-size: 11px;
    padding: 2px 10px;
    text-align: left;
    min-height: 22px;
}}
QPushButton#bookmark-chip:hover {{
    background: {SURFACE_3};
    color: {TEXT_PRIMARY};
}}
QPushButton#bookmark-chip:pressed {{
    color: {ACCENT};
}}
QPushButton#bookmarks-overflow {{
    background: transparent;
    border: none;
    border-radius: 4px;
    color: {TEXT_TERTIARY};
    font-size: 11px;
    padding: 2px 6px;
    min-width: 22px;
    max-width: 22px;
}}
QPushButton#bookmarks-overflow:hover {{
    background: {SURFACE_2};
    color: {TEXT_PRIMARY};
}}

/* ── Settings popup ──────────────────────────────────────────────────────── */
QWidget#settings-popup {{
    background: {SURFACE_1};
    border: 1px solid {BORDER_MED};
    border-radius: 10px;
}}
QLabel {{
    background: transparent;
}}
QLabel#settings-title {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
    font-weight: 600;
}}
QLabel#settings-section {{
    color: {TEXT_TERTIARY};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1px;
}}
QLabel#settings-label {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}
QCheckBox {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
    spacing: 8px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 4px;
    border: 1px solid {BORDER_MED};
    background: {SURFACE_2};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
}}
QLineEdit#settings-input {{
    background: {SURFACE_2};
    border: 1px solid {BORDER_MED};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 4px 10px;
    font-size: 12px;
    min-height: 26px;
}}
QLineEdit#settings-input:focus {{
    border: 1px solid {ACCENT};
}}
QPushButton#settings-apply {{
    background: {ACCENT};
    border: none;
    border-radius: 6px;
    color: #fff;
    font-size: 11px;
    font-weight: 600;
    padding: 4px 14px;
    min-height: 24px;
}}
QPushButton#settings-apply:hover {{
    background: {ACCENT_BRIGHT};
}}

/* ── Context menus ───────────────────────────────────────────────────────── */
QMenu {{
    background: {SURFACE_1};
    border: 1px solid {BORDER_MED};
    border-radius: 8px;
    padding: 4px 0px;
    color: {TEXT_PRIMARY};
    font-size: 12px;
    font-family: {FONT_FAMILY};
}}
QMenu::item {{
    padding: 7px 18px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background: {SURFACE_3};
}}
QMenu::separator {{
    height: 1px;
    background: {BORDER_FAINT};
    margin: 3px 0px;
}}

/* ── DevTools splitter ───────────────────────────────────────────────────── */
QSplitter::handle {{
    background: {BORDER_MED};
}}
QSplitter::handle:hover {{
    background: {ACCENT};
}}

/* ── Adblock indicator ───────────────────────────────────────────────────── */
QPushButton#adblock-btn {{
    background: transparent;
    border: none;
    border-left: 2px solid transparent;
    border-radius: 0px;
    min-width: 44px;
    max-width: 44px;
    min-height: 44px;
    max-height: 44px;
}}
QPushButton#adblock-btn:hover {{
    background: {SURFACE_2};
    border-left: 2px solid {ACCENT_GLOW};
}}
QPushButton#adblock-btn:pressed {{
    background: {SURFACE_3};
    border-left: 2px solid {ACCENT};
}}

/* ── Scrollbars ──────────────────────────────────────────────────────────── */
QScrollBar:horizontal {{
    height: 4px;
    background: transparent;
    border: none;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background: rgba(100,120,255,0.28);
    border-radius: 2px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
QScrollBar:vertical {{
    width: 4px;
    background: transparent;
    border: none;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: rgba(100,120,255,0.28);
    border-radius: 2px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
"""
