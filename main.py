import sys

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from ui.main_window import AxiomMainWindow


def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("AXIOM")
    app.setOrganizationName("Axiom")
    app.setApplicationDisplayName("AXIOM")

    window = AxiomMainWindow()
    _ = window  # keep reference alive

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
