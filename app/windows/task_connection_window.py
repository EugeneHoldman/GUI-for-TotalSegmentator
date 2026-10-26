"""Task Connection dialog for selecting tasks and structures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from PySide6.QtCore import QItemSelectionModel, QSignalBlocker, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView, QDialog

from app.structures_io import load_structures, save_structures
from ui_generated.ui_task_connection import Ui_TasksConnection


class TaskConnectionWindow(QDialog, Ui_TasksConnection):
    """Manage task/class connectivity and persist to structures.json on save."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Connected tasks")

        self._app_root = Path(__file__).resolve().parents[2]
        self._templates_dir = self._app_root / "Templates"
        self._totalseg_path = self._templates_dir / "totalsegmentator.json"
        self._structures_path = self._templates_dir / "structures.json"

        self._tasks_data: Dict[str, List[str]] = {}
        self._checked_map: Dict[str, Set[str]] = {}
        self._current_task: Optional[str] = None
        self._updating = False

        self._search_results: List[Tuple[str, Optional[str]]] = []
        self._search_index: int = -1

        self._tasks_model = QStandardItemModel(self.ConnectedTask)
        self.ConnectedTask.setModel(self._tasks_model)
        self.ConnectedTask.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.ConnectedTask.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self._classes_model = QStandardItemModel(self.ClassesInTask)
        self.ClassesInTask.setModel(self._classes_model)
        self.ClassesInTask.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ClassesInTask.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self._tasks_model.itemChanged.connect(self._on_task_item_changed)
        self._classes_model.itemChanged.connect(self._on_class_item_changed)

        selection = self.ConnectedTask.selectionModel()
        if selection is not None:
            selection.currentChanged.connect(self._on_task_current_changed)

        self.ConnectedTask.pressed.connect(self._on_task_pressed)

        self.Save.clicked.connect(self._on_save_clicked)
        self.pushButton_2.clicked.connect(self.close)
        self.ChooseAll.clicked.connect(self._on_choose_all_clicked)
        self.ChooseSelected.clicked.connect(self._on_choose_selected_clicked)
        self.Search.clicked.connect(self._on_search_clicked)
        self.NextResult.clicked.connect(self._on_next_result_clicked)
        self.SearchRequest.returnPressed.connect(self._on_search_clicked)

    def show(self) -> None:
        """Reload structures and tasks before showing the dialog."""
        self._load_data()
        super().show()

    def _load_data(self) -> None:
        self._tasks_data = self._load_tasks_from_totalseg()
        self._checked_map = self._load_checked_tasks()
        self._search_results = []
        self._search_index = -1
        preferred_task = self._current_task
        self._rebuild_task_list()
        self._ensure_task_selected(preferred_task)

    def _load_tasks_from_totalseg(self) -> Dict[str, List[str]]:
        """Load tasks/classes from Templates/totalsegmentator.json only."""
        try:
            with self._totalseg_path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            return {}
        tasks = data.get("tasks")
        if not isinstance(tasks, dict):
            return {}

        cleaned_tasks: Dict[str, List[str]] = {}
        for task_name, structures in tasks.items():
            if not isinstance(task_name, str) or not isinstance(structures, list):
                continue
            seen: Set[str] = set()
            unique_structures: List[str] = []
            for structure in structures:
                if isinstance(structure, str) and structure not in seen:
                    seen.add(structure)
                    unique_structures.append(structure)
            if unique_structures:
                cleaned_tasks[task_name] = sorted(unique_structures, key=str.lower)
        return cleaned_tasks

    def _load_checked_tasks(self) -> Dict[str, Set[str]]:
        data = load_structures(self._structures_path)
        tasks_section = data.get("tasks", data if isinstance(data, dict) else {})
        if not isinstance(tasks_section, dict):
            return {}
        checked: Dict[str, Set[str]] = {}
        for task_name, structures in tasks_section.items():
            if task_name not in self._tasks_data or not isinstance(structures, list):
                continue
            allowed = set(self._tasks_data.get(task_name, []))
            chosen = {s for s in structures if isinstance(s, str) and s in allowed}
            if chosen:
                checked[task_name] = chosen
        return checked

    def _rebuild_task_list(self) -> None:
        with QSignalBlocker(self._tasks_model):
            self._tasks_model.clear()
            for task_name in sorted(self._tasks_data.keys(), key=str.lower):
                item = QStandardItem(task_name)
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsUserCheckable
                )
                item.setCheckable(True)
                item.setCheckState(
                    Qt.CheckState.Checked
                    if self._checked_map.get(task_name)
                    else Qt.CheckState.Unchecked
                )
                self._tasks_model.appendRow(item)

    def _ensure_task_selected(self, preferred_task: Optional[str]) -> None:
        if preferred_task and self._set_current_task(preferred_task):
            return
        if self._tasks_model.rowCount() == 0:
            self._current_task = None
            self._populate_classes(None)
            return
        first_item = self._tasks_model.item(0)
        if first_item is not None:
            self._set_current_task(first_item.text())

    def _set_current_task(self, task_name: str) -> bool:
        selection = self.ConnectedTask.selectionModel()
        if selection is None:
            return False
        for row in range(self._tasks_model.rowCount()):
            item = self._tasks_model.item(row)
            if item is None or item.text() != task_name:
                continue
            index = item.index()
            already_current = selection.currentIndex() == index
            selection.setCurrentIndex(
                index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )
            self.ConnectedTask.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)
            self._current_task = task_name
            if already_current:
                # When selection does not change, manually refresh classes.
                self._populate_classes(task_name)
            return True
        return False

    def _on_task_pressed(self, index) -> None:  # noqa: ANN001
        self._select_task_by_index(index)

    def _on_task_current_changed(self, current, _previous) -> None:  # noqa: ANN001
        self._select_task_by_index(current)

    def _select_task_by_index(self, index) -> None:  # noqa: ANN001
        if not index.isValid():
            self._current_task = None
            self._populate_classes(None)
            return
        task_name = index.data(Qt.ItemDataRole.DisplayRole)
        if not isinstance(task_name, str) or task_name not in self._tasks_data:
            self._current_task = None
            self._populate_classes(None)
            return
        selection = self.ConnectedTask.selectionModel()
        if selection is not None and selection.currentIndex() != index:
            selection.setCurrentIndex(
                index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )
        self._current_task = task_name
        self._populate_classes(task_name)

    def _populate_classes(self, task_name: Optional[str]) -> None:
        self.ClassesInTask.setUpdatesEnabled(False)
        try:
            self._classes_model.clear()
            if not task_name:
                return
            selected = self._checked_map.get(task_name, set())
            for structure_name in self._tasks_data.get(task_name, []):
                item = QStandardItem(structure_name)
                item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled
                    | Qt.ItemFlag.ItemIsSelectable
                    | Qt.ItemFlag.ItemIsUserCheckable
                )
                item.setCheckable(True)
                item.setCheckState(
                    Qt.CheckState.Checked
                    if structure_name in selected
                    else Qt.CheckState.Unchecked
                )
                self._classes_model.appendRow(item)
        finally:
            self.ClassesInTask.setUpdatesEnabled(True)

    def _on_task_item_changed(self, item: QStandardItem) -> None:
        if self._updating:
            return
        task_name = item.text().strip()
        if not task_name or task_name not in self._tasks_data:
            return
        should_check = item.checkState() == Qt.CheckState.Checked
        all_classes = self._tasks_data.get(task_name, [])
        if should_check and all_classes:
            self._checked_map[task_name] = set(all_classes)
        else:
            self._checked_map.pop(task_name, None)
        if self._current_task == task_name:
            self._apply_class_check_state(self._checked_map.get(task_name, set()))

    def _on_class_item_changed(self, item: QStandardItem) -> None:
        if self._updating or not self._current_task:
            return
        structure_name = item.text().strip()
        if not structure_name:
            return
        selected = set(self._checked_map.get(self._current_task, set()))
        if item.checkState() == Qt.CheckState.Checked:
            selected.add(structure_name)
        else:
            selected.discard(structure_name)
        if selected:
            self._checked_map[self._current_task] = selected
        else:
            self._checked_map.pop(self._current_task, None)
        self._sync_task_check_state(self._current_task)

    def _sync_task_check_state(self, task_name: str) -> None:
        item = self._find_task_item(task_name)
        if item is None:
            return
        self._updating = True
        item.setCheckState(
            Qt.CheckState.Checked if self._checked_map.get(task_name) else Qt.CheckState.Unchecked
        )
        self._updating = False

    def _find_task_item(self, task_name: str) -> Optional[QStandardItem]:
        for row in range(self._tasks_model.rowCount()):
            item = self._tasks_model.item(row)
            if item is not None and item.text() == task_name:
                return item
        return None

    def _on_choose_all_clicked(self) -> None:
        if not self._current_task:
            return
        all_classes = self._tasks_data.get(self._current_task, [])
        if not all_classes:
            return
        current_selected = self._checked_map.get(self._current_task, set())
        check_all = len(current_selected) != len(all_classes)
        new_selection = set(all_classes) if check_all else set()
        if new_selection:
            self._checked_map[self._current_task] = new_selection
        else:
            self._checked_map.pop(self._current_task, None)
        self._apply_class_check_state(new_selection)
        self._sync_task_check_state(self._current_task)

    def _on_choose_selected_clicked(self) -> None:
        if not self._current_task:
            return
        selection = self.ClassesInTask.selectionModel()
        if selection is None or not selection.selectedIndexes():
            return
        selected_items = [
            self._classes_model.itemFromIndex(idx) for idx in selection.selectedIndexes() if idx.column() == 0
        ]
        target_check = any(item.checkState() == Qt.CheckState.Unchecked for item in selected_items)
        self._updating = True
        for item in selected_items:
            item.setCheckState(Qt.CheckState.Checked if target_check else Qt.CheckState.Unchecked)
        self._updating = False

        updated = set(self._checked_map.get(self._current_task, set()))
        for item in selected_items:
            name = item.text()
            if target_check:
                updated.add(name)
            else:
                updated.discard(name)
        if updated:
            self._checked_map[self._current_task] = updated
        else:
            self._checked_map.pop(self._current_task, None)
        self._sync_task_check_state(self._current_task)

    def _apply_class_check_state(self, selected: Set[str]) -> None:
        """Apply checkboxes in the class list to match the provided selection."""
        self.ClassesInTask.setUpdatesEnabled(False)
        self._updating = True
        try:
            for row in range(self._classes_model.rowCount()):
                item = self._classes_model.item(row)
                if item is None:
                    continue
                item.setCheckState(
                    Qt.CheckState.Checked if item.text() in selected else Qt.CheckState.Unchecked
                )
        finally:
            self._updating = False
            self.ClassesInTask.setUpdatesEnabled(True)

    def _on_save_clicked(self) -> None:
        payload: Dict[str, List[str]] = {}
        for task_name in sorted(self._checked_map.keys(), key=str.lower):
            structures = sorted(self._checked_map[task_name], key=str.lower)
            if structures:
                payload[task_name] = structures
        save_structures(self._structures_path, {"tasks": payload})

    def _on_search_clicked(self) -> None:
        query = self.SearchRequest.text().strip().lower()
        self._search_results = []
        self._search_index = -1
        if not query:
            return
        for task_name in sorted(self._tasks_data.keys(), key=str.lower):
            if query in task_name.lower():
                self._search_results.append((task_name, None))
            for structure in self._tasks_data.get(task_name, []):
                if query in structure.lower():
                    self._search_results.append((task_name, structure))
        if self._search_results:
            self._search_index = 0
            self._apply_search_result()

    def _on_next_result_clicked(self) -> None:
        if not self._search_results:
            self._on_search_clicked()
            return
        self._search_index = (self._search_index + 1) % len(self._search_results)
        self._apply_search_result()

    def _apply_search_result(self) -> None:
        if not (0 <= self._search_index < len(self._search_results)):
            return
        task_name, structure_name = self._search_results[self._search_index]
        if not self._set_current_task(task_name):
            return
        if structure_name:
            self._highlight_structure(structure_name)
        else:
            self.ConnectedTask.setFocus()

    def _highlight_structure(self, structure_name: str) -> None:
        selection = self.ClassesInTask.selectionModel()
        if selection is None:
            return
        for row in range(self._classes_model.rowCount()):
            item = self._classes_model.item(row)
            if item is None or item.text() != structure_name:
                continue
            index = item.index()
            selection.setCurrentIndex(
                index, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows
            )
            self.ClassesInTask.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtCenter)
            self.ClassesInTask.setFocus()
            return
