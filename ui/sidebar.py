"""
AXIOM Sidebar — left icon rail inspired by Opera GX, finished to Apple precision.

Layout (top → bottom):
  ┌──────┐
  │  ◆   │  Brand mark (non-interactive)
  │ ─── │  Separator
  │  ⊡   │  Bookmarks toggle
  │  ◷   │  History  (stub — ready for future)
  │  ↓   │  Downloads (stub — ready for future)
  │      │  ← flexible spacer
  │ [⬡]  │  Adblock indicator (live)
  │  ≡   │  Settings
  └──────┘
"""
from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt, QSize, QRect, QPoint
from PyQt6.QtGui import (
    QPainter, QColor, QPainterPath, QFont, QPen, QBrush,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QPushButton, QSizePolicy,
)

from core.adblock import AdBlockInterceptor
from ui.theme import (
    SURFACE_0, SURFACE_2, SURFACE_3, SURFACE_ACTIVE,
    BORDER_MED, BORDER_FAINT, ACCENT, ACCENT_BRIGHT, ACCENT_GLOW,
    ACCENT_DIM, TEXT_SECONDARY, TEXT_PRIMARY, TEXT_TERTIARY,
    SUCCESS, DANGER, FONT_FAMILY,
)

SIDEBAR_W = 46


# ---------------------------------------------------------------------------
# Brand mark widget
# ---------------------------------------------------------------------------

class _BrandMark(QWidget):
    """Painted AXIOM logo at the top of the sidebar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(SIDEBAR_W, 50)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() // 2, self.height() // 2

        # Outer hexagon ring
        ring_color = QColor(ACCENT)
        ring_color.setAlphaF(0.30)
        p.setPen(QPen(ring_color, 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        self._draw_hexagon(p, cx, cy, 13)

        # Inner fill
        fill = QColor(ACCENT)
        fill.setAlphaF(0.08)
        p.setBrush(QBrush(fill))
        p.setPen(Qt.PenStyle.NoPen)
        self._draw_hexagon(p, cx, cy, 11)

        # "A" letter
        p.setPen(QColor(ACCENT))
        f = QFont(FONT_FAMILY.split(",")[0].strip("'"), 10)
        f.setWeight(QFont.Weight.Bold)
        p.setFont(f)
        p.drawText(QRect(cx - 7, cy - 7, 14, 14), Qt.AlignmentFlag.AlignCenter, "A")

        p.end()

    @staticmethod
    def _draw_hexagon(p: QPainter, cx: int, cy: int, r: int):
        import math
        path = QPainterPath()
        for i in range(6):
            angle = math.radians(60 * i - 30)
            x = cx + r * math.cos(angle)
            y = cy + r * math.sin(angle)
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        path.closeSubpath()
        p.drawPath(path)


# ---------------------------------------------------------------------------
# Sidebar icon button
# ---------------------------------------------------------------------------

class _SidebarButton(QPushButton):
    def __init__(self, glyph: str, tooltip: str, parent=None):
        super().__init__(glyph, parent)
        self.setObjectName("sidebar-btn")
        self.setFixedSize(SIDEBAR_W, 44)
        self.setToolTip(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._active = False

    def set_active(self, active: bool):
        self._active = active
        self.setProperty("active", "true" if active else "false")
        # Force style refresh
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()


# ---------------------------------------------------------------------------
# Adblock sidebar button (custom-painted)
# ---------------------------------------------------------------------------

class _AdblockSidebarBtn(QPushButton):
    toggled_adblock = pyqtSignal(bool)

    def __init__(self, interceptor: AdBlockInterceptor, parent=None):
        super().__init__(parent)
        self.setObjectName("adblock-btn")
        self.setFixedSize(SIDEBAR_W, 44)
        self.setToolTip("Adblock: ON\nClick to toggle")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._interceptor = interceptor
        self.clicked.connect(self._on_click)

        from PyQt6.QtCore import QTimer
        self._timer = QTimer(self)
        self._timer.setInterval(2000)
        self._timer.timeout.connect(self.update)
        self._timer.start()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        enabled = self._interceptor.enabled
        cx, cy = self.width() // 2, self.height() // 2

        shield_color = QColor(SUCCESS if enabled else DANGER)
        p.setPen(QPen(shield_color, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)

        # Shield shape
        path = QPainterPath()
        sw, sh = 9, 11
        path.moveTo(cx, cy + sh)
        path.lineTo(cx - sw, cy + sh // 2)
        path.cubicTo(cx - sw, cy - sh, cx - sw, cy - sh, cx, cy - sh)
        path.cubicTo(cx + sw, cy - sh, cx + sw, cy - sh, cx + sw, cy + sh // 2)
        path.closeSubpath()
        p.drawPath(path)

        # Check mark inside when enabled
        if enabled:
            p.setPen(QPen(shield_color, 1.5))
            p.drawLine(cx - 3, cy, cx - 1, cy + 2)
            p.drawLine(cx - 1, cy + 2, cx + 4, cy - 3)

        # Badge count
        count = self._interceptor.blocked_count
        if count > 0 and enabled:
            badge_txt = f"{count}" if count < 100 else "99+"
            badge_bg = QColor(DANGER)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(badge_bg)
            badge_r = QRect(cx + 4, cy - 10, 14, 10)
            p.drawRoundedRect(badge_r, 5, 5)
            p.setPen(QColor("#FFFFFF"))
            f = QFont(FONT_FAMILY.split(",")[0].strip("'"), 6)
            f.setBold(True)
            p.setFont(f)
            p.drawText(badge_r, Qt.AlignmentFlag.AlignCenter, badge_txt)

        # Tooltip update
        status = "ON" if enabled else "OFF"
        tip = f"Adblock: {status}"
        if count > 0:
            tip += f" · {count} blocked"
        tip += "\nClick to toggle"
        self.setToolTip(tip)

        p.end()

    def _on_click(self):
        new_state = not self._interceptor.enabled
        self._interceptor.enabled = new_state
        self.toggled_adblock.emit(new_state)
        self.update()


# ---------------------------------------------------------------------------
# Sidebar separator
# ---------------------------------------------------------------------------

def _make_sep() -> QFrame:
    sep = QFrame()
    sep.setObjectName("sidebar-sep")
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setFixedHeight(1)
    sep.setStyleSheet(f"background: {BORDER_MED}; border: none; margin: 0 8px;")
    return sep


# ---------------------------------------------------------------------------
# Main sidebar widget
# ---------------------------------------------------------------------------

class AxiomSidebar(QWidget):
    bookmarks_toggled = pyqtSignal(bool)   # True = show, False = hide
    settings_requested = pyqtSignal()
    adblock_toggled = pyqtSignal(bool)
    # stubs for future
    history_requested = pyqtSignal()
    downloads_requested = pyqtSignal()

    def __init__(self, interceptor: AdBlockInterceptor, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(SIDEBAR_W)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        self._interceptor = interceptor
        self._bookmarks_active = True
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(0)

        # Brand mark
        layout.addWidget(_BrandMark())
        layout.addWidget(_make_sep())

        # ── Top section ──────────────────────────────
        self._bookmarks_btn = _SidebarButton("◈", "Bookmarks  (Ctrl+Shift+B)")
        self._bookmarks_btn.set_active(True)   # visible by default

        self._history_btn = _SidebarButton("◷", "History")
        self._downloads_btn = _SidebarButton("↓", "Downloads")

        for btn in (self._bookmarks_btn, self._history_btn, self._downloads_btn):
            layout.addWidget(btn)

        # Spacer
        layout.addStretch(1)

        # ── Bottom section ────────────────────────────
        layout.addWidget(_make_sep())

        self._adblock_btn = _AdblockSidebarBtn(self._interceptor)
        layout.addWidget(self._adblock_btn)

        self._settings_btn = _SidebarButton("≡", "Settings")
        layout.addWidget(self._settings_btn)

        # Connect
        self._bookmarks_btn.clicked.connect(self._on_bookmarks_clicked)
        self._history_btn.clicked.connect(self.history_requested)
        self._downloads_btn.clicked.connect(self.downloads_requested)
        self._adblock_btn.toggled_adblock.connect(self.adblock_toggled)
        self._settings_btn.clicked.connect(self.settings_requested)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_bookmarks_active(self, active: bool):
        self._bookmarks_active = active
        self._bookmarks_btn.set_active(active)

    def set_adblock_enabled(self, enabled: bool):
        self._interceptor.enabled = enabled
        self._adblock_btn.update()

    def settings_btn_widget(self) -> QPushButton:
        return self._settings_btn

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_bookmarks_clicked(self):
        self._bookmarks_active = not self._bookmarks_active
        self._bookmarks_btn.set_active(self._bookmarks_active)
        self.bookmarks_toggled.emit(self._bookmarks_active)
