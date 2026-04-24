import sys
from pathlib import Path

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import AxiomMainWindow

# Resolved relative to this file so it works from any working directory.
_ICON_PATH = Path(__file__).parent / "assets" / "axiom.png"


def _set_windows_app_id() -> None:
    """Tell Windows this is a standalone app, not python.exe.

    Without this call the taskbar groups AXIOM under the Python launcher icon
    and shows no custom icon. SetCurrentProcessExplicitAppUserModelID() pins
    the taskbar entry to our own AppID so Windows uses our icon.
    """
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Axiom.Browser.1"
        )
    except (AttributeError, OSError):
        pass   # Non-Windows or older shell32 — silently skip.


def main() -> None:
    _set_windows_app_id()

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("AXIOM")
    app.setOrganizationName("Axiom")
    app.setApplicationDisplayName("AXIOM")

    if _ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(_ICON_PATH)))

    window = AxiomMainWindow()
    _ = window  # keep reference alive

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
