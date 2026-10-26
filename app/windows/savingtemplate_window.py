"""Save Template dialog."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QMessageBox

from ui_generated.ui_savingtemplate import Ui_Dialog


class SavingTemplateWindow(QDialog, Ui_Dialog):
    """Dialog for capturing a new template name."""

    name_submitted = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Save Template")

        self.Create.clicked.connect(self._on_create_clicked)

    def show(self) -> None:
        """Reset the name field before showing the dialog."""
        self.NewName.clear()
        self.NewName.setFocus()
        super().show()

    def _on_create_clicked(self) -> None:
        name = self.NewName.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Enter a template name.")
            return
        self.name_submitted.emit(name)
        self.close()
