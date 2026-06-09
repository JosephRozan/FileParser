"""GUI entry point for FileParser."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from fileparser.ui.main_window import MainWindow


def main() -> int:
    import fileparser

    print(f"FileParser loaded from: {fileparser.__path__[0]}")
    app = QApplication(sys.argv)
    app.setApplicationName("FileParser")
    app.setOrganizationName("Wilmotte")
    window = MainWindow()
    window.setWindowTitle("FileParser — Wilmotte (dev)")
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
