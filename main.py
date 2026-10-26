"""Entry point for the TotalSegmentator UI application.

Imports stay light at module import-time to keep startup fast.
"""

from __future__ import annotations

import os
os.environ.setdefault("QT_SCALE_FACTOR_ROUNDING_POLICY", "PassThrough")
os.environ.setdefault("QT_STYLE_OVERRIDE", "Fusion")

import sys

from app.windows.main_window import MainWindow


def main() -> int:
    """Start the Qt event loop."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        raise SystemExit(
            "PySide6 is required. Install dependencies before running the UI."
        ) from exc

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
