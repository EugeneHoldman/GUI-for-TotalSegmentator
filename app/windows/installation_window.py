"""Installation settings dialog."""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox

from ui_generated.ui_installation import Ui_Dialog

SETTINGS_INSTALL_METHOD_KEY = "install_method"
SETTINGS_CONDA_ENV_PATH_KEY = "conda_env_path"
SETTINGS_TS_DEFAULT_KEY = "ts_weights_default"
SETTINGS_TS_WEIGHTS_PATH_KEY = "ts_weights_path"

INSTALL_METHOD_PIP = "pip"
INSTALL_METHOD_CONDA = "conda"


def _to_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False
    return default


class InstallationWindow(QDialog, Ui_Dialog):
    """Dialog for installation mode and optional TS weights directory."""

    def __init__(self, settings: QSettings, parent=None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Installation")

        self._settings = settings

        self.Pip.toggled.connect(self._on_install_method_toggled)
        self.TSDefault.toggled.connect(self._on_ts_default_toggled)
        self.BrowseToConda.clicked.connect(self._on_browse_conda_clicked)
        self.BrowseToTS.clicked.connect(self._on_browse_ts_clicked)

        self._restore_settings()

    def show(self) -> None:
        self._restore_settings()
        super().show()

    def accept(self) -> None:
        if self.Conda.isChecked():
            conda_path = Path(self.PathToConda.text().strip())
            if not conda_path.exists() or not conda_path.is_dir():
                QMessageBox.warning(
                    self,
                    "Installation",
                    "Please choose a valid conda environment folder before saving.",
                )
                return
            ts_executable = conda_path / "Scripts" / "TotalSegmentator.exe"
            combine_executable = conda_path / "Scripts" / "totalseg_combine_masks.exe"
            if not ts_executable.exists() or not combine_executable.exists():
                QMessageBox.warning(
                    self,
                    "Installation",
                    "Selected folder does not look like a valid conda environment for TotalSegmentator.",
                )
                return
        if not self.TSDefault.isChecked():
            ts_weights_path = Path(self.PathToTS.text().strip())
            if not ts_weights_path.exists() or not ts_weights_path.is_dir():
                QMessageBox.warning(
                    self,
                    "Installation",
                    "Please choose a valid TotalSegmentator weights folder before saving.",
                )
                return
        self._persist_settings()
        super().accept()

    def runtime_config(self) -> Dict[str, object]:
        """Return saved settings used by pipeline/command builders."""
        install_method = str(
            self._settings.value(SETTINGS_INSTALL_METHOD_KEY, INSTALL_METHOD_PIP)
        ).strip().lower()
        use_conda = install_method == INSTALL_METHOD_CONDA
        conda_path = str(self._settings.value(SETTINGS_CONDA_ENV_PATH_KEY, "")).strip()
        ts_default = _to_bool(self._settings.value(SETTINGS_TS_DEFAULT_KEY, True), True)
        ts_weights_path = str(self._settings.value(SETTINGS_TS_WEIGHTS_PATH_KEY, "")).strip()
        return {
            "use_conda": use_conda,
            "conda_env_path": conda_path if use_conda else "",
            "ts_weights_default": ts_default,
            "ts_weights_path": "" if ts_default else ts_weights_path,
        }

    def _restore_settings(self) -> None:
        install_method = str(
            self._settings.value(SETTINGS_INSTALL_METHOD_KEY, INSTALL_METHOD_PIP)
        ).strip().lower()
        conda_path = str(self._settings.value(SETTINGS_CONDA_ENV_PATH_KEY, "")).strip()
        ts_default = _to_bool(self._settings.value(SETTINGS_TS_DEFAULT_KEY, True), True)
        ts_weights_path = str(self._settings.value(SETTINGS_TS_WEIGHTS_PATH_KEY, "")).strip()

        if install_method == INSTALL_METHOD_CONDA:
            self.Conda.setChecked(True)
        else:
            self.Pip.setChecked(True)
        self.PathToConda.setText(conda_path)
        self.TSDefault.setChecked(ts_default)
        self.PathToTS.setText(ts_weights_path)
        self._update_install_method_state()
        self._update_ts_default_state()

    def _persist_settings(self) -> None:
        install_method = INSTALL_METHOD_CONDA if self.Conda.isChecked() else INSTALL_METHOD_PIP
        self._settings.setValue(SETTINGS_INSTALL_METHOD_KEY, install_method)
        self._settings.setValue(
            SETTINGS_CONDA_ENV_PATH_KEY,
            self.PathToConda.text().strip(),
        )
        self._settings.setValue(SETTINGS_TS_DEFAULT_KEY, self.TSDefault.isChecked())
        self._settings.setValue(
            SETTINGS_TS_WEIGHTS_PATH_KEY,
            self.PathToTS.text().strip(),
        )
        self._settings.sync()

    def _on_install_method_toggled(self, _checked: bool) -> None:
        self._update_install_method_state()

    def _on_ts_default_toggled(self, _checked: bool) -> None:
        self._update_ts_default_state()

    def _update_install_method_state(self) -> None:
        use_conda = self.Conda.isChecked()
        self.PathToConda.setEnabled(use_conda)
        self.BrowseToConda.setEnabled(use_conda)

    def _update_ts_default_state(self) -> None:
        use_default = self.TSDefault.isChecked()
        self.PathToTS.setEnabled(not use_default)
        self.BrowseToTS.setEnabled(not use_default)

    def _on_browse_conda_clicked(self) -> None:
        start_dir = self.PathToConda.text().strip() or str(Path.home())
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Conda Environment Folder",
            start_dir,
        )
        if selected_dir:
            self.PathToConda.setText(str(Path(selected_dir)))

    def _on_browse_ts_clicked(self) -> None:
        start_dir = self.PathToTS.text().strip() or str(Path.home())
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Select TotalSegmentator Weights Folder",
            start_dir,
        )
        if selected_dir:
            self.PathToTS.setText(str(Path(selected_dir)))
