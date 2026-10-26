"""Template Manager window controller."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QItemSelectionModel, QPersistentModelIndex, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QAbstractItemView, QMainWindow, QMessageBox

from app.structures_io import load_structures
from app.templates_io import list_templates, load_template, save_template
from app.windows.savingtemplate_window import SavingTemplateWindow
from ui_generated.ui_template_manager import Ui_MainWindow


class TemplateManagerWindow(QMainWindow, Ui_MainWindow):
    """Edit template contents using available structures."""

    templates_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowTitle("Template Manager")

        self._app_root = Path(__file__).resolve().parents[2]
        self._templates_dir = self._app_root / "Templates"
        self._structures_path = self._templates_dir / "structures.json"

        self._templates: Dict[str, Path] = {}
        self._saved_tasks: Dict[str, Dict[str, List[str]]] = {}
        self._overlay_tasks: Dict[str, Dict[str, List[str]]] = {}
        self._dirty_templates: set[str] = set()
        self._current_template: Optional[str] = None
        self._pending_name_handler: Optional[Callable[[str], None]] = None

        self._search_results: List[QPersistentModelIndex] = []
        self._search_index: int = -1

        self._saving_template_window = SavingTemplateWindow(self)
        self._saving_template_window.name_submitted.connect(self._on_name_submitted)

        self._template_model = QStandardItemModel(self.TemplName)
        self.TemplName.setModel(self._template_model)

        self._current_model = QStandardItemModel(self.CurrentStruct)
        self.CurrentStruct.setModel(self._current_model)
        self.CurrentStruct.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.CurrentStruct.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self._all_struct_model = QStandardItemModel(self.AllStruct)
        self.AllStruct.setModel(self._all_struct_model)
        self.AllStruct.setHeaderHidden(True)
        self.AllStruct.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.AllStruct.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.TemplName.currentIndexChanged.connect(self._on_template_selected)
        self.NewTempl.clicked.connect(self._on_new_template_clicked)
        self.Del.clicked.connect(self._on_delete_clicked)
        self.Add.clicked.connect(self._on_add_clicked)
        self.Remove.clicked.connect(self._on_remove_clicked)
        self.Save.clicked.connect(self._on_save_clicked)
        self.Save_3.clicked.connect(self._on_save_as_clicked)
        self.Reload.clicked.connect(self._on_reload_clicked)
        self.Exit.clicked.connect(self.close)
        self.Search.clicked.connect(self._on_search_clicked)
        self.NextResult.clicked.connect(self._on_next_result_clicked)
        self.SearchRequest.returnPressed.connect(self._on_search_clicked)

        self._set_template_controls_enabled(False)

    def show(self) -> None:
        """Refresh templates and structures before showing."""
        self._load_structures()
        self._load_templates()
        super().show()

    def _load_structures(self) -> None:
        data = load_structures(self._structures_path)
        tasks = data.get("tasks", {})
        if not isinstance(tasks, dict):
            tasks = {}

        self._all_struct_model.clear()
        for task_name in sorted(tasks.keys(), key=str.lower):
            task_item = QStandardItem(task_name)
            task_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            for structure_name in sorted(tasks.get(task_name, []) or []):
                if not isinstance(structure_name, str):
                    continue
                child = QStandardItem(structure_name)
                child.setData((task_name, structure_name), Qt.ItemDataRole.UserRole)
                child.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                task_item.appendRow(child)
            self._all_struct_model.appendRow(task_item)
        self.AllStruct.expandAll()

    def _load_templates(self) -> None:
        disk_templates: Dict[str, Path] = {}
        for entry in list_templates(self._templates_dir):
            name = entry.get("name")
            path = entry.get("path")
            if not isinstance(name, str) or not name:
                continue
            if isinstance(path, str):
                path = Path(path)
            if not isinstance(path, Path):
                continue
            disk_templates[name] = path

        merged: Dict[str, Path] = dict(disk_templates)
        for name, path in self._templates.items():
            if name not in merged and name in self._dirty_templates:
                merged[name] = path
        self._templates = merged

        if self._current_template not in self._templates:
            self._current_template = None

        self._rebuild_template_combo()
        self._refresh_current_struct()

    def _rebuild_template_combo(self) -> None:
        current = self._current_template
        self.TemplName.blockSignals(True)
        self._template_model.clear()
        for name in sorted(self._templates.keys(), key=str.lower):
            item = QStandardItem(name)
            if name in self._dirty_templates:
                font = item.font()
                font.setItalic(True)
                item.setFont(font)
            self._template_model.appendRow(item)
        self.TemplName.blockSignals(False)

        if current and current in self._templates:
            index = self.TemplName.findText(current)
            if index >= 0:
                self.TemplName.setCurrentIndex(index)
                return
        if self._templates:
            self.TemplName.setCurrentIndex(0)

    def _set_template_controls_enabled(self, enabled: bool) -> None:
        self.CurrentStruct.setEnabled(enabled)
        self.Add.setEnabled(enabled)
        self.Remove.setEnabled(enabled)
        self.Save.setEnabled(enabled)
        self.Save_3.setEnabled(enabled)
        self.Reload.setEnabled(enabled)
        self.Del.setEnabled(enabled)

    def _normalize_tasks(self, tasks: Dict[str, object]) -> Dict[str, List[str]]:
        normalized: Dict[str, List[str]] = {}
        for task_name, structures in tasks.items():
            if not isinstance(task_name, str) or not isinstance(structures, list):
                continue
            cleaned = sorted({item for item in structures if isinstance(item, str)})
            if cleaned:
                normalized[task_name] = cleaned
        return normalized

    def _clone_tasks(self, tasks: Dict[str, List[str]]) -> Dict[str, List[str]]:
        return {task: list(structures) for task, structures in tasks.items()}

    def _tasks_equal(
        self,
        left: Dict[str, List[str]],
        right: Dict[str, List[str]],
    ) -> bool:
        return self._normalize_tasks(left) == self._normalize_tasks(right)

    def _load_template_tasks(self, template_name: str) -> Dict[str, List[str]]:
        template_path = self._templates.get(template_name)
        if not template_path:
            return {}
        try:
            data = load_template(template_path)
        except (OSError, ValueError):
            return {}
        tasks = {}
        if isinstance(data, dict):
            tasks = data.get("tasks")
            if not isinstance(tasks, dict):
                tasks = data.get("structures") if isinstance(data.get("structures"), dict) else {}
        return self._normalize_tasks(tasks)

    def _ensure_template_loaded(self, template_name: str) -> None:
        if template_name in self._overlay_tasks:
            return
        tasks = self._load_template_tasks(template_name)
        self._saved_tasks[template_name] = self._clone_tasks(tasks)
        self._overlay_tasks[template_name] = self._clone_tasks(tasks)

    def _current_template_name(self) -> Optional[str]:
        name = self.TemplName.currentText().strip()
        if name:
            return name
        return None

    def _refresh_current_struct(self) -> None:
        name = self._current_template_name()
        if not name:
            self._current_model.clear()
            self._set_template_controls_enabled(False)
            self._current_template = None
            return
        self._current_template = name
        self._ensure_template_loaded(name)
        overlay_tasks = self._overlay_tasks.get(name, {})
        saved_tasks = self._saved_tasks.get(name, {})

        saved_pairs = {
            (task_name, structure_name)
            for task_name, structures in saved_tasks.items()
            for structure_name in structures
        }

        self._current_model.clear()
        pairs: List[Tuple[str, str]] = []
        for task_name, structures in overlay_tasks.items():
            for structure_name in structures:
                pairs.append((task_name, structure_name))
        for task_name, structure_name in sorted(pairs, key=lambda item: (item[0], item[1])):
            item = QStandardItem(f"{task_name}: {structure_name}")
            item.setData((task_name, structure_name), Qt.ItemDataRole.UserRole)
            item.setEditable(False)
            if (task_name, structure_name) not in saved_pairs:
                font = item.font()
                font.setItalic(True)
                item.setFont(font)
            self._current_model.appendRow(item)
        self._set_template_controls_enabled(True)

    def _update_dirty_state(self, template_name: str) -> None:
        saved = self._saved_tasks.get(template_name, {})
        overlay = self._overlay_tasks.get(template_name, {})
        if self._tasks_equal(saved, overlay):
            self._dirty_templates.discard(template_name)
        else:
            self._dirty_templates.add(template_name)
        self._rebuild_template_combo()

    def _on_template_selected(self, index: int) -> None:  # noqa: ARG002 - Qt slot
        self._search_results = []
        self._search_index = -1
        self._refresh_current_struct()

    def _on_new_template_clicked(self) -> None:
        self._request_template_name(self._create_new_template)

    def _create_new_template(self, requested_name: str) -> None:
        template_name = self._unique_template_name(requested_name)
        safe_base = self._sanitize_template_filename(template_name)
        template_path = self._unique_template_path(safe_base)

        save_template(template_path, {"template_name": template_name, "tasks": {}})
        self._templates[template_name] = template_path
        self._saved_tasks[template_name] = {}
        self._overlay_tasks[template_name] = {}
        self._dirty_templates.discard(template_name)
        self._current_template = template_name

        self._rebuild_template_combo()
        self._refresh_current_struct()
        self.templates_changed.emit()

    def _on_delete_clicked(self) -> None:
        name = self._current_template_name()
        if not name:
            return
        confirm = QMessageBox.question(
            self,
            "Delete template",
            f"Delete template '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        template_path = self._templates.get(name)
        if template_path and template_path.exists():
            try:
                template_path.unlink()
            except OSError:
                QMessageBox.warning(self, "Delete failed", "Unable to delete the template file.")
                return
        self._templates.pop(name, None)
        self._saved_tasks.pop(name, None)
        self._overlay_tasks.pop(name, None)
        self._dirty_templates.discard(name)
        self._current_template = None

        self._rebuild_template_combo()
        self._refresh_current_struct()
        self.templates_changed.emit()

    def _on_add_clicked(self) -> None:
        name = self._current_template_name()
        if not name:
            return
        self._ensure_template_loaded(name)
        selection = self.AllStruct.selectionModel()
        if selection is None:
            return
        pairs = self._collect_allstruct_pairs(selection.selectedIndexes())
        if not pairs:
            return
        overlay = self._overlay_tasks.get(name, {})
        for task_name, structure_name in pairs:
            bucket = overlay.setdefault(task_name, [])
            if structure_name not in bucket:
                bucket.append(structure_name)
        overlay = self._normalize_tasks(overlay)
        self._overlay_tasks[name] = overlay
        self._update_dirty_state(name)
        self._refresh_current_struct()

    def _on_remove_clicked(self) -> None:
        name = self._current_template_name()
        if not name:
            return
        selection = self.CurrentStruct.selectionModel()
        if selection is None:
            return
        selected = selection.selectedIndexes()
        if not selected:
            return
        to_remove: set[Tuple[str, str]] = set()
        for index in selected:
            payload = index.data(Qt.ItemDataRole.UserRole)
            if isinstance(payload, (list, tuple)) and len(payload) == 2:
                task_name, structure_name = payload
                if isinstance(task_name, str) and isinstance(structure_name, str):
                    to_remove.add((task_name, structure_name))
        if not to_remove:
            return
        overlay = self._overlay_tasks.get(name, {})
        for task_name, structure_name in to_remove:
            structures = overlay.get(task_name, [])
            if structure_name in structures:
                updated = [item for item in structures if item != structure_name]
                if updated:
                    overlay[task_name] = updated
                else:
                    overlay.pop(task_name, None)
        overlay = self._normalize_tasks(overlay)
        self._overlay_tasks[name] = overlay
        self._update_dirty_state(name)
        self._refresh_current_struct()

    def _on_save_clicked(self) -> None:
        name = self._current_template_name()
        if not name:
            return
        template_path = self._templates.get(name)
        if not template_path:
            QMessageBox.warning(self, "Save failed", "Template path is missing.")
            return
        overlay = self._normalize_tasks(self._overlay_tasks.get(name, {}))
        save_template(template_path, {"template_name": name, "tasks": overlay})
        self._saved_tasks[name] = self._clone_tasks(overlay)
        self._overlay_tasks[name] = self._clone_tasks(overlay)
        self._dirty_templates.discard(name)
        self._rebuild_template_combo()
        self._refresh_current_struct()
        self.templates_changed.emit()

    def _on_save_as_clicked(self) -> None:
        source_template = self._current_template_name()
        if not source_template:
            return
        self._request_template_name(lambda new_name: self._save_as_template(source_template, new_name))

    def _on_reload_clicked(self) -> None:
        """Restore CurrentStruct to the last saved state for the selected template."""
        name = self._current_template_name()
        if not name:
            return
        self._ensure_template_loaded(name)
        saved = self._saved_tasks.get(name, {})
        self._overlay_tasks[name] = self._clone_tasks(saved)
        self._dirty_templates.discard(name)
        self._rebuild_template_combo()
        self._refresh_current_struct()

    def _save_as_template(
        self,
        source_template: str,
        requested_name: str,
    ) -> None:
        self._ensure_template_loaded(source_template)
        overlay_source = self._overlay_tasks.get(source_template)
        if overlay_source is None:
            return
        overlay = self._normalize_tasks(overlay_source)
        template_name = self._unique_template_name(requested_name)
        safe_base = self._sanitize_template_filename(template_name)
        template_path = self._unique_template_path(safe_base)

        save_template(template_path, {"template_name": template_name, "tasks": overlay})

        self._templates[template_name] = template_path
        self._saved_tasks[template_name] = self._clone_tasks(overlay)
        self._overlay_tasks[template_name] = self._clone_tasks(overlay)
        self._dirty_templates.discard(template_name)

        self._current_template = template_name
        self._rebuild_template_combo()
        self._refresh_current_struct()
        self.templates_changed.emit()

    def _collect_allstruct_pairs(self, indexes) -> List[Tuple[str, str]]:  # noqa: ANN001
        pairs: set[Tuple[str, str]] = set()
        for index in indexes:
            if index.column() != 0:
                continue
            item = self._all_struct_model.itemFromIndex(index)
            if item is None:
                continue
            if item.hasChildren():
                task_name = item.text().strip()
                if not task_name:
                    continue
                for row in range(item.rowCount()):
                    child = item.child(row)
                    if child is None:
                        continue
                    structure_name = child.text().strip()
                    if structure_name:
                        pairs.add((task_name, structure_name))
            else:
                parent = item.parent()
                task_name = parent.text().strip() if parent else ""
                structure_name = item.text().strip()
            if task_name and structure_name:
                pairs.add((task_name, structure_name))
        return sorted(pairs, key=lambda item: (item[0], item[1]))

    def _unique_template_name(self, name: str) -> str:
        base_name = name.strip() or "template"
        existing = {template.lower() for template in self._templates.keys()}
        if base_name.lower() not in existing:
            return base_name
        counter = 2
        while True:
            candidate = f"{base_name}_{counter}"
            if candidate.lower() not in existing:
                return candidate
            counter += 1

    def _sanitize_template_filename(self, name: str) -> str:
        cleaned: List[str] = []
        for char in name.strip().lower():
            if "a" <= char <= "z" or "0" <= char <= "9":
                cleaned.append(char)
            elif char in (" ", "-", "_"):
                cleaned.append("_")
        base = "".join(cleaned)
        while "__" in base:
            base = base.replace("__", "_")
        base = base.strip("_")
        return base or "template"

    def _unique_template_path(self, base_name: str) -> Path:
        candidate = self._templates_dir / f"{base_name}.json"
        if not candidate.exists() and candidate not in self._templates.values():
            return candidate
        counter = 2
        while True:
            candidate = self._templates_dir / f"{base_name}_{counter}.json"
            if not candidate.exists() and candidate not in self._templates.values():
                return candidate
            counter += 1

    def _request_template_name(self, handler: Callable[[str], None]) -> None:
        self._pending_name_handler = handler
        self._saving_template_window.show()
        self._saving_template_window.raise_()
        self._saving_template_window.activateWindow()

    def _on_name_submitted(self, name: str) -> None:
        name = name.strip()
        if not name:
            return
        handler = self._pending_name_handler
        self._pending_name_handler = None
        if handler:
            handler(name)

    def _on_search_clicked(self) -> None:
        query = self.SearchRequest.text().strip()
        self._search_results = []
        self._search_index = -1
        if not query:
            return
        needle = query.lower()
        for row in range(self._all_struct_model.rowCount()):
            task_item = self._all_struct_model.item(row)
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
        selection.select(target, QItemSelectionModel.ClearAndSelect | QItemSelectionModel.Rows)
        self.AllStruct.scrollTo(target, QAbstractItemView.ScrollHint.PositionAtCenter)
