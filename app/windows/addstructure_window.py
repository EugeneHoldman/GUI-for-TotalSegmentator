"""Add Structure dialog."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from PySide6.QtCore import QItemSelectionModel, QPersistentModelIndex, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView, QDialog

from app.structures_io import load_structures
from ui_generated.ui_addstructure import Ui_Dialog


class AddStructureWindow(QDialog, Ui_Dialog):
    """Dialog for selecting structures to add to the current overlay."""

    structures_selected = Signal(list)

    def __init__(self, structures_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Add Structure")

        self._structures_path = Path(structures_path)
        self._model = QStandardItemModel(self.AllStruct)
        self.AllStruct.setModel(self._model)
        self.AllStruct.setHeaderHidden(True)
        self.AllStruct.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.AllStruct.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self._search_results: List[QPersistentModelIndex] = []
        self._search_index: int = -1

        self.Save.clicked.connect(self._on_save_clicked)
        self.pushButton.clicked.connect(self.close)
        self.Search.clicked.connect(self._on_search_clicked)
        self.NextResult.clicked.connect(self._on_next_result_clicked)
        self.SearchRequest.returnPressed.connect(self._on_search_clicked)

    def refresh_structures(self) -> None:
        """Reload structures.json and rebuild the task/class tree."""
        data = load_structures(self._structures_path)
        tasks = data.get("tasks", {})
        if not isinstance(tasks, dict):
            tasks = {}

        self._model.clear()
        self._search_results = []
        self._search_index = -1
        for task_name in sorted(tasks.keys()):
            task_item = QStandardItem(task_name)
            task_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
            for structure_name in sorted(tasks.get(task_name, []) or []):
                if not isinstance(structure_name, str):
                    continue
                child = QStandardItem(structure_name)
                child.setData((task_name, structure_name), Qt.ItemDataRole.UserRole)
                child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                task_item.appendRow(child)
            self._model.appendRow(task_item)
        self.AllStruct.expandAll()

    def show(self) -> None:
        """Ensure the tree reflects the latest structures.json before showing."""
        self.refresh_structures()
        super().show()

    def _extract_pair(self, index) -> Tuple[str, str] | None:  # noqa: ANN001 - Qt index
        payload = index.data(Qt.ItemDataRole.UserRole)
        if isinstance(payload, (list, tuple)) and len(payload) == 2:
            task_name, structure_name = payload
            if isinstance(task_name, str) and isinstance(structure_name, str):
                return task_name, structure_name

        parent = index.parent()
        if parent.isValid():
            task_name = parent.data(Qt.ItemDataRole.DisplayRole)
            structure_name = index.data(Qt.ItemDataRole.DisplayRole)
            if isinstance(task_name, str) and isinstance(structure_name, str):
                return task_name, structure_name
        return None

    def _on_save_clicked(self) -> None:
        selection = self.AllStruct.selectionModel()
        if selection is None:
            return
        selected_pairs: List[Tuple[str, str]] = []
        seen: set[Tuple[str, str]] = set()
        for index in selection.selectedIndexes():
            if index.column() != 0:
                continue
            pair = self._extract_pair(index)
            if pair and pair not in seen:
                seen.add(pair)
                selected_pairs.append(pair)
        if selected_pairs:
            self.structures_selected.emit(selected_pairs)
        self.close()

    def _on_search_clicked(self) -> None:
        query = self.SearchRequest.text().strip()
        self._search_results = []
        self._search_index = -1
        if not query:
            return
        needle = query.lower()
        for row in range(self._model.rowCount()):
            task_item = self._model.item(row)
            if task_item is None:
                continue
            for child_row in range(task_item.rowCount()):
                child_item = task_item.child(child_row)
                if child_item is None:
                    continue
                if needle in child_item.text().lower():
                    self._search_results.append(QPersistentModelIndex(child_item.index()))
        if self._search_results:
            self._search_index = 0
            self._select_search_result(self._search_index)

    def _on_next_result_clicked(self) -> None:
        if not self._search_results:
            self._on_search_clicked()
            return
        self._search_index = (self._search_index + 1) % len(self._search_results)
        self._select_search_result(self._search_index)

    def _select_search_result(self, index: int) -> None:
        if not (0 <= index < len(self._search_results)):
            return
        target = self._search_results[index]
        if not target.isValid():
            return
        parent = target.parent()
        if parent.isValid():
            self.AllStruct.expand(parent)
        selection = self.AllStruct.selectionModel()
        if selection is None:
            return
        selection.clearSelection()
        selection.select(
            target, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
        )
        self.AllStruct.scrollTo(
            target, QAbstractItemView.ScrollHint.PositionAtCenter
        )
