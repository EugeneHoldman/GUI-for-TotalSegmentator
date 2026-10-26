"""License window for setting the TotalSegmentator license key."""

from __future__ import annotations

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QDialog

from ui_generated.ui_license import Ui_Dialog


def _last_nonempty_line(text: str) -> str | None:
    for line in reversed(text.splitlines()):
        stripped = line.strip()
        if stripped:
            return stripped
    return None


class LicenseWindow(QDialog, Ui_Dialog):
    """Dialog that sets the license key using totalseg_set_license."""

    def __init__(self, logger, parent=None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("License")
        self._logger = logger
        self._process: QProcess | None = None

        self.pushButton.clicked.connect(self._on_validate_clicked)
        self.pushButton_2.clicked.connect(self.close)

    def _on_validate_clicked(self) -> None:
        if self._process is not None:
            return
        key = self.KeyValue.text().strip()
        if not key:
            self._logger.error("License validation FAILED.", detail="Empty license key.")
            return
        self._logger.info("License validation started \u2026")
        self.pushButton.setEnabled(False)

        process = QProcess(self)
        process.setProgram("totalseg_set_license")
        process.setArguments(["-l", key])
        process.finished.connect(self._on_process_finished)
        process.errorOccurred.connect(self._on_process_error)
        self._process = process
        process.start()

    def _on_process_error(self, _error) -> None:  # noqa: ANN001 - Qt signature
        if self._process is None:
            return
        detail = self._process.errorString()
        self._logger.error("License validation FAILED.", detail=detail)
        self._reset_process()

    def _on_process_finished(self, exit_code: int, exit_status) -> None:  # noqa: ANN001
        if self._process is None:
            return
        stdout = bytes(self._process.readAllStandardOutput()).decode(
            "utf-8", errors="ignore"
        ).strip()
        stderr = bytes(self._process.readAllStandardError()).decode(
            "utf-8", errors="ignore"
        ).strip()

        if exit_status != QProcess.ExitStatus.NormalExit or exit_code != 0:
            detail = _last_nonempty_line(stderr) or _last_nonempty_line(stdout) or "Unknown error"
            self._logger.error("License validation FAILED.", detail=detail)
        else:
            self._logger.info("License validation OK.")
        self._reset_process()

    def _reset_process(self) -> None:
        self.pushButton.setEnabled(True)
        if self._process is not None:
            self._process.deleteLater()
            self._process = None
