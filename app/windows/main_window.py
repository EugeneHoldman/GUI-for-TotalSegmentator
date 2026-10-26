"""Main window controller for the TotalSegmentator UI."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from html import escape as html_escape
from pathlib import Path
import shutil
from threading import Event
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import (
    QByteArray,
    QAbstractTableModel,
    QItemSelectionModel,
    QMimeData,
    QModelIndex,
    QObject,
    QSettings,
    QSignalBlocker,
    QThread,
    Qt,
    Signal,
)
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractItemDelegate,
    QComboBox,
    QFileDialog,
    QHeaderView,
    QMainWindow,
    QMessageBox,
    QStyledItemDelegate,
)

from app.patient_scan import scan_patients
from app.pipeline import run_pipeline
from app.templates_io import list_templates, load_template, save_template
from app.windows.addstructure_window import AddStructureWindow
from app.windows.installation_window import InstallationWindow
from app.windows.license_window import LicenseWindow
from app.windows.savingtemplate_window import SavingTemplateWindow
from app.windows.task_connection_window import TaskConnectionWindow
from app.windows.template_manager_window import TemplateManagerWindow
from ui_generated.ui_mainwindow import Ui_MainWindow

TABLE_WIDTH_PX = 750
ID_COL_MAX_PX = 235

AVAIL_NAME_COL_PX = 435
AVAIL_CT_COL_PX = 70
AVAIL_NIFTI_COL_PX = 70
AVAIL_RTSS_COL_PX = 70

QUEUE_NAME_COL_PX = 340
QUEUE_TEMPLATE_COL_PX = 250

SETTINGS_ORG = "TotalSegmentatorUI"
SETTINGS_APP = "TotalSegmentatorUI"
SETTINGS_PATIENT_ROOT_KEY = "patients_root"
SETTINGS_DELETE_SEGM_KEY = "delete_segmentations"
SETTINGS_DELETE_CT_KEY = "delete_ct"
SETTINGS_TO_RTSS_KEY = "to_rtss"
SETTINGS_TO_RTSS_POSTPROC_KEY = "to_rtss_postproc"
SETTINGS_AUTO_OPEN_KEY = "auto_open"

# Queue row keys for template selection and per-patient overlays.
TEMPLATE_KEY = "template"
TEMPLATE_PATH_KEY = "template_path"
TEMPLATE_TASKS_KEY = "template_tasks"
OVERLAY_TASKS_KEY = "overlay_tasks"
PATIENT_DIR_KEY = "patient_dir"
SCAN_DIR_KEY = "scan_dir"


class ExecutionStatusLogger(QObject):
    """Append timestamped log messages to the ExecutionStatus widget."""

    message_ready = Signal(str)

    def __init__(self, output_widget) -> None:
        super().__init__(output_widget)
        self._output = output_widget
        self.message_ready.connect(self._append_message)

    def info(self, message: str) -> None:
        self._emit("INFO", message, is_error=False)

    def warn(self, message: str) -> None:
        self._emit("WARN", message, is_error=False)

    def error(self, message: str, detail: str | None = None) -> None:
        self._emit("ERROR", message, is_error=True, detail=detail)

    def _emit(self, level: str, message: str, is_error: bool, detail: str | None = None) -> None:
        """Format messages as `HH:MM:SS LEVEL  text` with optional red error detail."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"{timestamp} {level:<5} {message}"
        html_line = html_escape(line).replace("\n", "<br>")
        if is_error:
            html_line = f'<span style="color:#b00020;">{html_line}</span>'
        else:
            # Force rich-text rendering so escaped entities (e.g. &quot;) display as literal characters.
            html_line = f"<span>{html_line}</span>"
        self.message_ready.emit(html_line)
        if detail:
            detail_text = html_escape(str(detail)).replace("\n", "<br>")
            if is_error:
                detail_text = f'<span style=\"color:#b00020;\">{detail_text}</span>'
            else:
                detail_text = f"<span>{detail_text}</span>"
            self.message_ready.emit(detail_text)

    def _append_message(self, html_line: str) -> None:
        self._output.append(html_line)


class PipelineWorker(QObject):
    """Run the segmentation pipeline in a background thread."""

    results_ready = Signal(list)
    finished = Signal()

    def __init__(
        self,
        patients_root: Path,
        queue_rows: List[dict],
        totalseg_config_path: Path,
        options: Dict[str, object],
        logger: ExecutionStatusLogger,
    ) -> None:
        super().__init__()
        self._patients_root = Path(patients_root)
        self._queue_rows = queue_rows
        self._totalseg_config_path = Path(totalseg_config_path)
        self._options = options
        self._logger = logger
        self._stop_event = Event()

    def request_stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        results = run_pipeline(
            patients_root=self._patients_root,
            queue_rows=self._queue_rows,
            totalseg_config_path=self._totalseg_config_path,
            options=self._options,
            logger=self._logger,
            should_stop=self._stop_event.is_set,
        )
        self.results_ready.emit(results)
        self.finished.emit()


class TemplateComboDelegate(QStyledItemDelegate):
    """Combo box delegate for selecting templates in the queue."""

    template_chosen = Signal(QModelIndex, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._template_names: List[str] = []

    def set_templates(self, names: List[str]) -> None:
        self._template_names = list(names)

    def createEditor(self, parent, option, index):  # noqa: ANN001 - Qt signature
        combo = QComboBox(parent)
        combo.addItem("")
        for name in self._template_names:
            combo.addItem(name)
        combo.activated.connect(lambda _index, editor=combo: self._commit_and_close(editor))
        return combo

    def setEditorData(self, editor, index) -> None:  # noqa: ANN001 - Qt signature
        current = index.data(Qt.DisplayRole) or ""
        match = editor.findText(current)
        editor.setCurrentIndex(match if match >= 0 else 0)

    def setModelData(self, editor, model, index) -> None:  # noqa: ANN001 - Qt signature
        name = editor.currentText().strip()
        self.template_chosen.emit(index, name)

    def _commit_and_close(self, editor) -> None:
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QAbstractItemDelegate.EndEditHint.NoHint)


class PatientTableModel(QAbstractTableModel):
    """Model for the AvailablePatients table."""

    HEADERS = ["ID", "Name, Surname", "CT", "NIfTI", "RTSS"]

    def __init__(self, rows: List[dict] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._rows = rows or []

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802 - Qt API
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802 - Qt API
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):  # noqa: ANN001
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        column = index.column()
        if role == Qt.TextAlignmentRole and column in (2, 3, 4):
            return Qt.AlignCenter
        if role not in (Qt.DisplayRole, Qt.ToolTipRole):
            return None
        if column == 0:
            return row.get("patient_id", "")
        if column == 1:
            return row.get("name", "")
        if column == 2:
            return "Yes" if row.get("has_ct") else "No"
        if column == 3:
            return "Yes" if row.get("has_nifti") else "No"
        if column == 4:
            return "Yes" if row.get("has_rtss") else "No"
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: ANN001
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        if 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        return None

    def row_data(self, row_index: int) -> dict | None:
        if 0 <= row_index < len(self._rows):
            return self._rows[row_index]
        return None

    def set_rows(self, rows: List[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rows(self) -> List[dict]:
        return list(self._rows)

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:  # noqa: ANN001
        if not self._rows or not (0 <= column < len(self.HEADERS)):
            return
        reverse = order == Qt.SortOrder.DescendingOrder

        def key(row: dict):
            if column == 0:
                return str(row.get("patient_id", "")).lower()
            if column == 1:
                return str(row.get("name", "")).lower()
            if column == 2:
                return (0 if row.get("has_ct") else 1, str(row.get("patient_id", "")).lower())
            if column == 3:
                return (0 if row.get("has_nifti") else 1, str(row.get("patient_id", "")).lower())
            if column == 4:
                return (0 if row.get("has_rtss") else 1, str(row.get("patient_id", "")).lower())
            return str(row.get("patient_id", "")).lower()

        self.beginResetModel()
        self._rows = sorted(self._rows, key=key, reverse=reverse)
        self.endResetModel()


class QueueTableModel(QAbstractTableModel):
    """Model for the SegmQueue table."""

    HEADERS = ["ID", "Name, Surname", "Template"]
    MIME_TYPE = "application/x-segmqueue-rows"

    def __init__(self, rows: List[dict] | None = None, parent=None) -> None:
        super().__init__(parent)
        self._rows = rows or []

    def rowCount(self, parent=QModelIndex()) -> int:  # noqa: N802 - Qt API
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:  # noqa: N802 - Qt API
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):  # noqa: ANN001
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        row = self._rows[index.row()]
        column = index.column()
        if column == 0:
            return row.get("patient_id", "")
        if column == 1:
            return row.get("name", "")
        if column == 2:
            return row.get(TEMPLATE_KEY, "")
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):  # noqa: ANN001
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return None
        if 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:  # noqa: N802 - Qt API
        base_flags = Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if index.isValid():
            flags = base_flags | Qt.ItemIsDragEnabled | Qt.ItemIsDropEnabled
            if index.column() == 2:
                flags |= Qt.ItemIsEditable
            return flags
        return Qt.ItemIsDropEnabled

    def supportedDropActions(self) -> Qt.DropActions:  # noqa: N802 - Qt API
        return Qt.MoveAction

    def supportedDragActions(self) -> Qt.DropActions:  # noqa: N802 - Qt API
        return Qt.MoveAction

    def mimeTypes(self) -> List[str]:  # noqa: N802 - Qt API
        return [self.MIME_TYPE]

    def mimeData(self, indexes: List[QModelIndex]) -> QMimeData:  # noqa: N802 - Qt API
        mime_data = QMimeData()
        rows = sorted({index.row() for index in indexes})
        payload = ",".join(str(row) for row in rows)
        mime_data.setData(self.MIME_TYPE, QByteArray(payload.encode("utf-8")))
        return mime_data

    def dropMimeData(  # noqa: N802 - Qt API, PLR0913 - Qt signature
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        if action == Qt.IgnoreAction:
            return True
        if not data.hasFormat(self.MIME_TYPE):
            return False
        payload = bytes(data.data(self.MIME_TYPE)).decode("utf-8")
        if not payload:
            return False
        try:
            rows = [int(part) for part in payload.split(",") if part != ""]
        except ValueError:
            return False
        rows = sorted(set(rows))
        if not rows:
            return False

        if row == -1:
            row = parent.row() if parent.isValid() else self.rowCount()

        row = max(0, min(row, self.rowCount()))
        return self._move_rows(rows, row)

    def _move_rows(self, rows: List[int], destination_row: int) -> bool:
        # Move the selected rows as a contiguous block while preserving order.
        if not rows:
            return False
        moving_rows = [self._rows[index] for index in rows if 0 <= index < len(self._rows)]
        if not moving_rows:
            return False
        remaining = [row for idx, row in enumerate(self._rows) if idx not in set(rows)]

        rows_before = sum(1 for idx in rows if idx < destination_row)
        insert_row = destination_row - rows_before
        insert_row = max(0, min(insert_row, len(remaining)))

        new_rows = remaining[:insert_row] + moving_rows + remaining[insert_row:]
        if new_rows == self._rows:
            return True
        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()
        return True

    def append_rows(self, rows: List[dict]) -> None:
        if not rows:
            return
        start = len(self._rows)
        end = start + len(rows) - 1
        self.beginInsertRows(QModelIndex(), start, end)
        self._rows.extend(rows)
        self.endInsertRows()

    def remove_rows(self, rows: List[int]) -> None:
        if not rows:
            return
        to_remove = set(rows)
        new_rows = [row for idx, row in enumerate(self._rows) if idx not in to_remove]
        if new_rows == self._rows:
            return
        self.beginResetModel()
        self._rows = new_rows
        self.endResetModel()

    def row_data(self, row_index: int) -> dict | None:
        if 0 <= row_index < len(self._rows):
            return self._rows[row_index]
        return None

    def set_row_data(self, row_index: int, row_data: dict) -> None:
        if not (0 <= row_index < len(self._rows)):
            return
        self._rows[row_index] = row_data
        top_left = self.index(row_index, 0)
        bottom_right = self.index(row_index, self.columnCount() - 1)
        self.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole])

    def find_row_by_patient_id(self, patient_id: str) -> Optional[int]:
        for index, row in enumerate(self._rows):
            if row.get("patient_id") == patient_id:
                return index
        return None

    def rows(self) -> List[dict]:
        return list(self._rows)

    def set_rows(self, rows: List[dict]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def sort(self, column: int, order: Qt.SortOrder = Qt.AscendingOrder) -> None:  # noqa: ANN001
        if not self._rows or not (0 <= column < len(self.HEADERS)):
            return
        reverse = order == Qt.SortOrder.DescendingOrder

        def key(row: dict):
            if column == 0:
                return str(row.get("patient_id", "")).lower()
            if column == 1:
                return str(row.get("name", "")).lower()
            if column == 2:
                return str(row.get(TEMPLATE_KEY, "")).lower()
            return str(row.get("patient_id", "")).lower()

        self.beginResetModel()
        self._rows = sorted(self._rows, key=key, reverse=reverse)
        self.endResetModel()


class MainWindow(QMainWindow, Ui_MainWindow):
    """Main window wiring and table behavior."""

    def __init__(self) -> None:
        super().__init__()
        self.setupUi(self)
        self.setWindowTitle("TotalSegmentator UI")
        self._execution_logger = ExecutionStatusLogger(self.ExecutionStatus)
        self._settings = QSettings(SETTINGS_ORG, SETTINGS_APP)
        self._patients_root: Path | None = None
        self._pipeline_thread: QThread | None = None
        self._pipeline_worker: PipelineWorker | None = None
        self._pipeline_results: List[dict] = []

        self._patients_model = PatientTableModel()
        self.AvailablePatients.setModel(self._patients_model)

        self._queue_model = QueueTableModel()
        self.SegmQueue.setModel(self._queue_model)

        self._configure_table(self.AvailablePatients, enable_sort=True)
        self._configure_table(self.SegmQueue, enable_drag_drop=True, enable_template_edit=True, enable_sort=False)
        self._apply_available_columns()
        self._apply_queue_columns()

        self._app_root = Path(__file__).resolve().parents[2]
        self._templates_dir = self._app_root / "Templates"
        self._structures_path = self._templates_dir / "structures.json"
        self._templates: Dict[str, Path] = {}

        self._template_delegate = TemplateComboDelegate(self.SegmQueue)
        self._template_delegate.template_chosen.connect(self._on_template_chosen)
        self.SegmQueue.setItemDelegateForColumn(2, self._template_delegate)

        self._templ_struct_model = QStandardItemModel(self.TemplStruct)
        self.TemplStruct.setModel(self._templ_struct_model)
        self.TemplStruct.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.TemplStruct.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)

        self._add_structure_window = AddStructureWindow(self._structures_path, self)
        self._add_structure_window.structures_selected.connect(self._on_structures_added)
        self._saving_template_window = SavingTemplateWindow(self)
        self._saving_template_window.name_submitted.connect(self._on_template_name_submitted)
        self._template_manager_window = TemplateManagerWindow(self)
        self._template_manager_window.templates_changed.connect(self._load_templates)
        self._task_connection_window = TaskConnectionWindow(self)
        self._license_window = LicenseWindow(self._execution_logger, self)
        self._installation_window = InstallationWindow(self._settings, self)
        self._pending_overlay_patient_id: Optional[str] = None
        self._pending_save_patient_id: Optional[str] = None
        self._active_template_patient_id: Optional[str] = None

        self._load_templates()
        self._set_template_controls_enabled(False)
        self._restore_run_options()

        self.Refresh.clicked.connect(self._on_refresh_clicked)
        self.Browse.clicked.connect(self._on_browse_clicked)
        self.AddToQueue.clicked.connect(self._on_add_to_queue_clicked)
        self.RemoveFromQueue.clicked.connect(self._on_remove_from_queue_clicked)
        self.ClearQueue.clicked.connect(self._on_clear_queue_clicked)
        self.DelPatients.clicked.connect(self._on_delete_patients_clicked)
        self.AddStructure.clicked.connect(self._on_add_structure_clicked)
        self.RemoveStructure.clicked.connect(self._on_remove_structure_clicked)
        self.ResetToOrig.clicked.connect(self._on_reset_to_orig_clicked)
        self.SaveAsNew.clicked.connect(self._on_save_as_new_clicked)
        self.Start.clicked.connect(self._on_start_clicked)
        self.Stop.clicked.connect(self._on_stop_clicked)
        self.actionTemplate_manager.triggered.connect(self._on_template_manager_triggered)
        self.actionConnected_tasks.triggered.connect(self._on_task_connection_triggered)
        self.actionLicense.triggered.connect(self._on_license_triggered)
        self.actionInstallation.triggered.connect(self._on_installation_triggered)
        self.DelSegm.toggled.connect(self._on_simple_option_toggled)
        self.DelCTscans.toggled.connect(self._on_simple_option_toggled)
        self.AutoOpen.toggled.connect(self._on_simple_option_toggled)
        self.ToRTSS.toggled.connect(self._on_rtss_toggled)
        self.ToRTSS_postproc.toggled.connect(self._on_rtss_postproc_toggled)

        queue_selection = self.SegmQueue.selectionModel()
        if queue_selection is not None:
            queue_selection.selectionChanged.connect(self._on_queue_selection_changed)
            queue_selection.currentChanged.connect(self._on_queue_current_changed)
        self.SegmQueue.clicked.connect(self._on_queue_clicked)

        self._queue_model.modelReset.connect(self._open_template_editors_for_all)
        self._queue_model.rowsInserted.connect(self._open_template_editors_for_rows)

        self._restore_patients_root()
        self._queue_selected_rows: List[int] = []
        self.Stop.setEnabled(False)

    def _on_template_manager_triggered(self) -> None:
        self._template_manager_window.show()

    def _on_task_connection_triggered(self) -> None:
        self._task_connection_window.show()

    def _on_license_triggered(self) -> None:
        self._license_window.show()

    def _on_installation_triggered(self) -> None:
        self._installation_window.show()

    def _on_start_clicked(self) -> None:
        if self._pipeline_thread is not None and self._pipeline_thread.isRunning():
            QMessageBox.information(self, "Pipeline", "A pipeline run is already in progress.")
            return
        root_text = self.CTscans.text().strip()
        patients_root = Path(root_text) if root_text else None
        if not patients_root or not patients_root.exists() or not patients_root.is_dir():
            QMessageBox.warning(self, "Pipeline", "Patients root is missing or invalid.")
            return
        queue_rows = deepcopy(self._queue_model.rows())
        if not queue_rows:
            QMessageBox.warning(self, "Pipeline", "Queue is empty.")
            return
        available_by_id: Dict[str, dict] = {}
        for patient_row in self._patients_model.rows():
            patient_id = str(patient_row.get("patient_id") or "").strip()
            if patient_id and patient_id not in available_by_id:
                available_by_id[patient_id] = patient_row
        for queue_row in queue_rows:
            if not isinstance(queue_row, dict):
                continue
            queue_id = str(queue_row.get("patient_id") or "").strip()
            source_row = available_by_id.get(queue_id)
            if source_row is None:
                continue
            if not queue_row.get(PATIENT_DIR_KEY):
                queue_row[PATIENT_DIR_KEY] = source_row.get(PATIENT_DIR_KEY)
            if not queue_row.get(SCAN_DIR_KEY):
                queue_row[SCAN_DIR_KEY] = source_row.get(SCAN_DIR_KEY) or source_row.get(
                    PATIENT_DIR_KEY
                )
        self._pipeline_results = []

        to_rtss = self.ToRTSS.isChecked() or self.ToRTSS_postproc.isChecked()
        options = {
            "to_rtss": to_rtss,
            "to_rtss_postproc": self.ToRTSS_postproc.isChecked(),
            "delete_ct": self.DelCTscans.isChecked(),
            "delete_segmentations": self.DelSegm.isChecked(),
            "auto_open": self.AutoOpen.isChecked(),
        }
        options.update(self._installation_window.runtime_config())

        worker = PipelineWorker(
            patients_root=patients_root,
            queue_rows=queue_rows,
            totalseg_config_path=self._templates_dir / "totalsegmentator.json",
            options=options,
            logger=self._execution_logger,
        )
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.results_ready.connect(self._on_pipeline_results_ready)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_pipeline_finished)

        self._pipeline_thread = thread
        self._pipeline_worker = worker
        self.Start.setEnabled(False)
        self.Stop.setEnabled(True)
        thread.start()

    def _on_stop_clicked(self) -> None:
        if self._pipeline_thread is None or not self._pipeline_thread.isRunning():
            return
        if self._pipeline_worker is None:
            return
        self._execution_logger.warn("Stop requested. Waiting for the current step to stop.")
        self._pipeline_worker.request_stop()
        self.Stop.setEnabled(False)

    def _on_pipeline_results_ready(self, results) -> None:  # noqa: ANN001 - Qt slot
        if isinstance(results, list):
            self._pipeline_results = [item for item in results if isinstance(item, dict)]
        else:
            self._pipeline_results = []

    def _on_pipeline_finished(self) -> None:
        successful_refs = {
            str(item.get("queue_ref") or "").strip()
            for item in self._pipeline_results
            if item.get("status") == "ok" and str(item.get("queue_ref") or "").strip()
        }
        if successful_refs:
            self._remove_queue_patients(successful_refs)
        self._pipeline_results = []
        self.Start.setEnabled(True)
        self.Stop.setEnabled(False)
        self._pipeline_thread = None
        self._pipeline_worker = None

    def _configure_table(
        self,
        table,
        enable_drag_drop: bool = False,
        enable_template_edit: bool = False,
        enable_sort: bool = False,
    ) -> None:
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        if enable_template_edit:
            table.setEditTriggers(
                QAbstractItemView.EditTrigger.DoubleClicked
                | QAbstractItemView.EditTrigger.EditKeyPressed
            )
        else:
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        header.setSortIndicatorShown(enable_sort)
        table.setSortingEnabled(enable_sort)
        if enable_drag_drop:
            table.setDragEnabled(True)
            table.setAcceptDrops(True)
            table.setDropIndicatorShown(True)
            table.setDragDropOverwriteMode(False)
            table.setDefaultDropAction(Qt.MoveAction)
            table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

    def _apply_available_columns(self) -> None:
        self.AvailablePatients.setColumnWidth(1, AVAIL_NAME_COL_PX)
        self.AvailablePatients.setColumnWidth(2, AVAIL_CT_COL_PX)
        self.AvailablePatients.setColumnWidth(3, AVAIL_NIFTI_COL_PX)
        self.AvailablePatients.setColumnWidth(4, AVAIL_RTSS_COL_PX)
        self._apply_id_column(self.AvailablePatients, 0)

    def _apply_queue_columns(self) -> None:
        self.SegmQueue.setColumnWidth(1, QUEUE_NAME_COL_PX)
        self.SegmQueue.setColumnWidth(2, QUEUE_TEMPLATE_COL_PX)
        self._apply_id_column(self.SegmQueue, 0)
        self._open_template_editors_for_all()

    def _apply_id_column(self, table, column_index: int) -> None:
        # Fit ID to content with a hard cap to keep the layout stable.
        table.resizeColumnToContents(column_index)
        if table.columnWidth(column_index) > ID_COL_MAX_PX:
            table.setColumnWidth(column_index, ID_COL_MAX_PX)

    def _restore_run_options(self) -> None:
        """Restore run option checkboxes with defaults and enforce exclusivity."""
        del_segm = self._get_bool_setting(SETTINGS_DELETE_SEGM_KEY, True)
        del_ct = self._get_bool_setting(SETTINGS_DELETE_CT_KEY, True)
        to_rtss = self._get_bool_setting(SETTINGS_TO_RTSS_KEY, False)
        to_rtss_postproc = self._get_bool_setting(SETTINGS_TO_RTSS_POSTPROC_KEY, False)
        auto_open = self._get_bool_setting(SETTINGS_AUTO_OPEN_KEY, False)

        with QSignalBlocker(self.DelSegm):
            self.DelSegm.setChecked(del_segm)
        with QSignalBlocker(self.DelCTscans):
            self.DelCTscans.setChecked(del_ct)
        with QSignalBlocker(self.AutoOpen):
            self.AutoOpen.setChecked(auto_open)

        if to_rtss_postproc:
            with QSignalBlocker(self.ToRTSS_postproc):
                self.ToRTSS_postproc.setChecked(True)
            with QSignalBlocker(self.ToRTSS):
                self.ToRTSS.setChecked(False)
        else:
            with QSignalBlocker(self.ToRTSS):
                self.ToRTSS.setChecked(to_rtss)
            with QSignalBlocker(self.ToRTSS_postproc):
                self.ToRTSS_postproc.setChecked(False)
        self._update_cleanup_option_state()
        self._persist_run_options()

    def _get_bool_setting(self, key: str, default: bool) -> bool:
        value = self._settings.value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "y", "on"}:
                return True
            if lowered in {"false", "0", "no", "n", "off"}:
                return False
        return bool(default)

    def _restore_patients_root(self) -> None:
        saved_root = self._settings.value(SETTINGS_PATIENT_ROOT_KEY, "")
        if isinstance(saved_root, str) and saved_root.strip():
            candidate = Path(saved_root)
            self.CTscans.setText(str(candidate))
            self._patients_root = candidate

    def _persist_patients_root(self, patients_root: Path) -> None:
        self._patients_root = patients_root
        self._settings.setValue(SETTINGS_PATIENT_ROOT_KEY, str(patients_root))
        self._settings.sync()

    def _has_usable_patients(self, records: List[dict]) -> bool:
        return bool(records)

    def _handle_invalid_patients_root(
        self,
        message: str,
        revert_to: Path | None,
        *,
        show_dialog: bool,
    ) -> None:
        if show_dialog:
            QMessageBox.warning(self, "Patients folder", f"{message}\nKeeping the previous folder.")
        if revert_to is not None:
            self.CTscans.setText(str(revert_to))

    def _apply_patients_root(
        self,
        patients_root: Path,
        *,
        show_dialog: bool,
        revert_to: Path | None,
    ) -> bool:
        if not patients_root.exists() or not patients_root.is_dir():
            self._handle_invalid_patients_root(
                "Patients folder is missing or invalid.",
                revert_to,
                show_dialog=show_dialog,
            )
            return False

        records = scan_patients(patients_root, force_rescan=True)
        if not self._has_usable_patients(records):
            self._handle_invalid_patients_root(
                "Selected folder contains no patients with usable CT or RTSS data.",
                revert_to,
                show_dialog=show_dialog,
            )
            return False

        self._persist_patients_root(patients_root)
        self.CTscans.setText(str(patients_root))
        self._patients_model.set_rows(records)
        self._apply_available_columns()
        return True

    def _persist_run_options(self) -> None:
        self._settings.setValue(SETTINGS_DELETE_SEGM_KEY, self.DelSegm.isChecked())
        self._settings.setValue(SETTINGS_DELETE_CT_KEY, self.DelCTscans.isChecked())
        self._settings.setValue(SETTINGS_TO_RTSS_KEY, self.ToRTSS.isChecked())
        self._settings.setValue(SETTINGS_TO_RTSS_POSTPROC_KEY, self.ToRTSS_postproc.isChecked())
        self._settings.setValue(SETTINGS_AUTO_OPEN_KEY, self.AutoOpen.isChecked())
        self._settings.sync()

    def _on_simple_option_toggled(self, _checked: bool) -> None:
        self._persist_run_options()

    def _on_rtss_toggled(self, checked: bool) -> None:
        if checked and self.ToRTSS_postproc.isChecked():
            with QSignalBlocker(self.ToRTSS_postproc):
                self.ToRTSS_postproc.setChecked(False)
        self._update_cleanup_option_state()
        self._persist_run_options()

    def _on_rtss_postproc_toggled(self, checked: bool) -> None:
        if checked and self.ToRTSS.isChecked():
            with QSignalBlocker(self.ToRTSS):
                self.ToRTSS.setChecked(False)
        self._update_cleanup_option_state()
        self._persist_run_options()

    def _update_cleanup_option_state(self) -> None:
        """Enable cleanup flags only for RTSS modes; grey out in NIfTI-only mode."""
        rtss_mode = self.ToRTSS.isChecked() or self.ToRTSS_postproc.isChecked()
        self.DelSegm.setEnabled(rtss_mode)
        self.DelCTscans.setEnabled(rtss_mode)
        if rtss_mode:
            self.DelSegm.setToolTip("")
            self.DelCTscans.setToolTip("")
            return
        hint = "Available only in RTSS modes."
        self.DelSegm.setToolTip(hint)
        self.DelCTscans.setToolTip(hint)

    def _load_templates(self) -> None:
        """Refresh template name -> path mapping from disk."""
        self._templates = {}
        for entry in list_templates(self._templates_dir):
            name = entry.get("name")
            path = entry.get("path")
            if not isinstance(name, str) or not name:
                continue
            if isinstance(path, str):
                path = Path(path)
            if not isinstance(path, Path):
                continue
            if name not in self._templates:
                self._templates[name] = path
        template_names = sorted(self._templates.keys(), key=str.lower)
        self._template_delegate.set_templates(template_names)
        self._refresh_template_editors()

    def _open_template_editors_for_rows(self, parent, start: int, end: int) -> None:  # noqa: ANN001
        for row in range(start, end + 1):
            index = self._queue_model.index(row, 2)
            if index.isValid():
                self.SegmQueue.openPersistentEditor(index)

    def _open_template_editors_for_all(self) -> None:
        for row in range(self._queue_model.rowCount()):
            index = self._queue_model.index(row, 2)
            if index.isValid():
                self.SegmQueue.openPersistentEditor(index)

    def _refresh_template_editors(self) -> None:
        for row in range(self._queue_model.rowCount()):
            index = self._queue_model.index(row, 2)
            if index.isValid():
                self.SegmQueue.closePersistentEditor(index)
                self.SegmQueue.openPersistentEditor(index)

    def _normalize_tasks(self, tasks: Dict[str, object]) -> Dict[str, List[str]]:
        """Normalize task payloads into unique, ordered string lists."""
        normalized: Dict[str, List[str]] = {}
        for task_name, structures in tasks.items():
            if not isinstance(task_name, str) or not isinstance(structures, list):
                continue
            seen: set[str] = set()
            cleaned: List[str] = []
            for structure_name in structures:
                if not isinstance(structure_name, str):
                    continue
                if structure_name in seen:
                    continue
                seen.add(structure_name)
                cleaned.append(structure_name)
            if cleaned:
                normalized[task_name] = cleaned
        return normalized

    def _clone_tasks(self, tasks: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """Copy task -> structure lists so overlays stay per-patient."""
        return {task: list(structures) for task, structures in tasks.items()}

    def _load_template_tasks(self, template_name: str) -> Dict[str, List[str]]:
        """Load and normalize tasks for a single template."""
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

    def _selected_queue_rows(self) -> List[int]:
        selection = self.SegmQueue.selectionModel()
        if selection is None:
            return []
        return sorted({index.row() for index in selection.selectedRows()})

    def _current_queue_row(self) -> Optional[int]:
        selection = self.SegmQueue.selectionModel()
        if selection is None:
            return self._queue_model.find_row_by_patient_id(self._active_template_patient_id or "")
        current = selection.currentIndex()
        if current.isValid():
            row = current.row()
            row_data = self._queue_model.row_data(row)
            if row_data and row_data.get("patient_id"):
                self._active_template_patient_id = row_data.get("patient_id")
            return current.row()
        selected = selection.selectedRows()
        if selected:
            row = sorted(selected, key=lambda index: index.row())[0].row()
            row_data = self._queue_model.row_data(row)
            if row_data and row_data.get("patient_id"):
                self._active_template_patient_id = row_data.get("patient_id")
            return row
        if self._active_template_patient_id:
            return self._queue_model.find_row_by_patient_id(self._active_template_patient_id)
        return None

    def _set_template_controls_enabled(self, enabled: bool) -> None:
        self.TemplStruct.setEnabled(enabled)
        self.AddStructure.setEnabled(enabled)
        self.RemoveStructure.setEnabled(enabled)
        self.ResetToOrig.setEnabled(enabled)
        self.SaveAsNew.setEnabled(enabled)

    def _clear_templ_struct(self) -> None:
        self._templ_struct_model.clear()

    def _extract_task_structure(self, payload, display_text: str | None) -> Tuple[str, str] | None:
        if isinstance(payload, (list, tuple)) and len(payload) == 2:
            task_name, structure_name = payload
            if isinstance(task_name, str) and isinstance(structure_name, str):
                return task_name, structure_name
        text = payload if isinstance(payload, str) else display_text
        if isinstance(text, str) and ":" in text:
            task_name, _, structure_name = text.partition(":")
            task_name = task_name.strip()
            structure_name = structure_name.strip()
            if task_name and structure_name:
                return task_name, structure_name
        return None

    def _populate_templ_struct(self, overlay_tasks: Dict[str, List[str]]) -> None:
        # Display task + structure pairs with task metadata kept in UserRole.
        self._templ_struct_model.clear()
        pairs: List[Tuple[str, str]] = []
        for task_name, structures in overlay_tasks.items():
            for structure_name in structures:
                pairs.append((task_name, structure_name))
        for task_name, structure_name in sorted(pairs, key=lambda item: (item[0], item[1])):
            item = QStandardItem(f"{task_name}: {structure_name}")
            item.setData((task_name, structure_name), Qt.ItemDataRole.UserRole)
            item.setEditable(False)
            self._templ_struct_model.appendRow(item)

    def _refresh_template_controls(self, force_row: Optional[int] = None) -> None:
        row_index = force_row if force_row is not None else self._current_queue_row()
        if row_index is None:
            self._clear_templ_struct()
            self._set_template_controls_enabled(False)
            return
        row = self._queue_model.row_data(row_index)
        if not row or not row.get(TEMPLATE_KEY):
            self._clear_templ_struct()
            self._set_template_controls_enabled(False)
            return
        if row.get("patient_id"):
            self._active_template_patient_id = row.get("patient_id")
        overlay_tasks = row.get(OVERLAY_TASKS_KEY) or row.get(TEMPLATE_TASKS_KEY) or {}
        # If overlay was unexpectedly empty, restore it from the template tasks so the UI stays in sync.
        if overlay_tasks and not row.get(OVERLAY_TASKS_KEY):
            row[OVERLAY_TASKS_KEY] = self._clone_tasks(overlay_tasks)
            self._queue_model.set_row_data(row_index, row)
        self._populate_templ_struct(overlay_tasks)
        self._set_template_controls_enabled(True)

    def _on_refresh_clicked(self) -> None:
        root_text = self.CTscans.text().strip()
        if not root_text:
            self._handle_invalid_patients_root(
                "Patients folder is missing or invalid.",
                self._patients_root,
                show_dialog=True,
            )
            return
        patients_root = Path(root_text)
        self._apply_patients_root(
            patients_root,
            show_dialog=True,
            revert_to=self._patients_root,
        )

    def _on_browse_clicked(self) -> None:
        start_dir = str(self._patients_root) if self._patients_root else str(Path.home())
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Patients Folder",
            start_dir,
        )
        if not selected_dir:
            return
        self.CTscans.setText(str(Path(selected_dir)))

    def _on_add_to_queue_clicked(self) -> None:
        selection = self.AvailablePatients.selectionModel()
        if selection is None:
            return
        selected_rows = selection.selectedRows()
        if not selected_rows:
            return
        selected_rows = sorted(selected_rows, key=lambda index: index.row())

        existing_refs = {self._queue_row_ref(row) for row in self._queue_model.rows()}
        new_rows: List[dict] = []
        for index in selected_rows:
            row_data = self._patients_model.row_data(index.row())
            if not row_data:
                continue
            patient_id = row_data.get("patient_id")
            patient_dir = row_data.get(PATIENT_DIR_KEY)
            scan_dir = row_data.get(SCAN_DIR_KEY) or patient_dir
            patient_ref = str(scan_dir or patient_dir or patient_id or "")
            if not patient_id or not patient_ref or patient_ref in existing_refs:
                continue
            existing_refs.add(patient_ref)
            new_rows.append(
                {
                    "patient_id": patient_id,
                    "name": row_data.get("name", ""),
                    PATIENT_DIR_KEY: patient_dir,
                    SCAN_DIR_KEY: scan_dir,
                    TEMPLATE_KEY: "",
                    TEMPLATE_PATH_KEY: None,
                    TEMPLATE_TASKS_KEY: {},
                    OVERLAY_TASKS_KEY: {},
                }
            )
        self._queue_model.append_rows(new_rows)
        self._apply_queue_columns()

    def _on_remove_from_queue_clicked(self) -> None:
        selection = self.SegmQueue.selectionModel()
        if selection is None:
            return
        selected_rows = selection.selectedRows()
        if not selected_rows:
            return
        rows = sorted({index.row() for index in selected_rows})
        active_id = self._active_template_patient_id
        if active_id:
            removing_ids = {
                self._queue_model.row_data(row).get("patient_id")
                for row in rows
                if self._queue_model.row_data(row)
            }
            if active_id in removing_ids:
                self._active_template_patient_id = None
        self._queue_model.remove_rows(rows)
        self._apply_queue_columns()
        self._refresh_template_controls()

    def _on_clear_queue_clicked(self) -> None:
        self._active_template_patient_id = None
        self._queue_model.set_rows([])
        self._apply_queue_columns()
        self._refresh_template_controls()

    def _queue_row_ref(self, row: dict) -> str:
        return str(row.get(SCAN_DIR_KEY) or row.get(PATIENT_DIR_KEY) or row.get("patient_id") or "")

    def _remove_queue_patients(self, patient_refs: set[str]) -> None:
        if not patient_refs:
            return
        removing_ids: set[str] = set()
        rows = [
            index
            for index, row in enumerate(self._queue_model.rows())
            if self._queue_row_ref(row) in patient_refs
        ]
        for row_index in rows:
            row_data = self._queue_model.row_data(row_index)
            if row_data and row_data.get("patient_id"):
                removing_ids.add(str(row_data.get("patient_id")))
        if not rows:
            return
        if self._active_template_patient_id in removing_ids:
            self._active_template_patient_id = None
        self._queue_model.remove_rows(rows)
        self._apply_queue_columns()
        self._refresh_template_controls()

    def _on_delete_patients_clicked(self) -> None:
        selection = self.AvailablePatients.selectionModel()
        if selection is None:
            return
        selected_rows = selection.selectedRows()
        if not selected_rows:
            return
        root_text = self.CTscans.text().strip()
        patients_root = Path(root_text) if root_text else None
        if not patients_root or not patients_root.exists() or not patients_root.is_dir():
            QMessageBox.warning(self, "Delete patients", "Patients root is missing or invalid.")
            return

        patient_items: List[Tuple[str, Path]] = []
        for index in sorted(selected_rows, key=lambda item: item.row()):
            row_data = self._patients_model.row_data(index.row())
            if not row_data:
                continue
            patient_id = row_data.get("patient_id")
            if not patient_id:
                continue
            raw_dir = row_data.get(PATIENT_DIR_KEY)
            patient_dir = Path(raw_dir) if isinstance(raw_dir, str) and raw_dir.strip() else (patients_root / str(patient_id))
            if not patient_dir.is_absolute():
                patient_dir = patients_root / patient_dir
            patient_items.append((str(patient_id), patient_dir))
        if not patient_items:
            return

        confirm = QMessageBox.question(
            self,
            "Delete patients",
            f"Delete {len(patient_items)} patient(s)? This will permanently remove their folders.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return

        deleted: List[str] = []
        failed: List[str] = []
        missing: List[str] = []
        root_resolved = patients_root.resolve()
        for patient_id, patient_dir in patient_items:
            try:
                patient_resolved = patient_dir.resolve()
            except OSError:
                failed.append(patient_id)
                continue
            if patient_resolved == root_resolved or root_resolved not in patient_resolved.parents:
                failed.append(patient_id)
                continue
            if not patient_dir.exists():
                missing.append(patient_id)
                continue
            if not patient_dir.is_dir():
                failed.append(patient_id)
                continue
            try:
                shutil.rmtree(patient_dir)
                deleted.append(patient_id)
            except OSError:
                failed.append(patient_id)

        deleted_refs = {
            str(patient_dir)
            for patient_id, patient_dir in patient_items
            if patient_id in deleted or patient_id in missing
        }
        self._remove_queue_patients(deleted_refs)
        summary_lines: List[str] = []
        if deleted:
            summary_lines.append(f"Deleted patients: {', '.join(deleted)}.")
        if missing:
            summary_lines.append(f"Missing folders (not deleted): {', '.join(missing)}.")
        if failed:
            summary_lines.append(f"Failed to delete: {', '.join(failed)}.")
        if summary_lines:
            QMessageBox.information(self, "Delete patients", "\n".join(summary_lines))
        self._on_refresh_clicked()

    def _on_queue_selection_changed(self, selected, deselected) -> None:  # noqa: ANN001
        selection = self.SegmQueue.selectionModel()
        if selection is not None:
            current = selection.currentIndex()
            if current.isValid():
                row = self._queue_model.row_data(current.row())
                if row and row.get("patient_id"):
                    self._active_template_patient_id = row.get("patient_id")
            self._queue_selected_rows = sorted({index.row() for index in selection.selectedRows()})
        self._refresh_template_controls()

    def _on_queue_current_changed(self, current, previous) -> None:  # noqa: ANN001
        if not current.isValid():
            return
        row = self._queue_model.row_data(current.row())
        if row and row.get("patient_id"):
            self._active_template_patient_id = row.get("patient_id")
        self._refresh_template_controls(force_row=current.row())

    def _on_queue_clicked(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        row = self._queue_model.row_data(index.row())
        if row and row.get("patient_id"):
            self._active_template_patient_id = row.get("patient_id")
        self._refresh_template_controls(force_row=index.row())

    def _on_template_chosen(self, index: QModelIndex, template_name: str) -> None:
        if index.isValid():
            row = self._queue_model.row_data(index.row())
            if row and row.get("patient_id"):
                self._active_template_patient_id = row.get("patient_id")
        selection = self.SegmQueue.selectionModel()
        if selection is not None and index.isValid():
            selection.setCurrentIndex(index, QItemSelectionModel.NoUpdate)
        selected_rows = self._queue_selected_rows or self._selected_queue_rows()
        if index.isValid():
            selected_rows = sorted(set(selected_rows + [index.row()]))
        if not selected_rows:
            return
        focus_row = index.row() if index.isValid() else None
        self._apply_template_to_rows(selected_rows, template_name, focus_row=focus_row)
        # Ensure TemplStruct refreshes immediately for the row where the template was chosen.
        if focus_row is not None:
            focus_row_data = self._queue_model.row_data(focus_row)
            if focus_row_data and focus_row_data.get(TEMPLATE_KEY):
                overlay_tasks = (
                    focus_row_data.get(OVERLAY_TASKS_KEY)
                    or focus_row_data.get(TEMPLATE_TASKS_KEY)
                    or {}
                )
                if overlay_tasks and not focus_row_data.get(OVERLAY_TASKS_KEY):
                    focus_row_data[OVERLAY_TASKS_KEY] = self._clone_tasks(overlay_tasks)
                    self._queue_model.set_row_data(focus_row, focus_row_data)
                self._populate_templ_struct(overlay_tasks)
                self._set_template_controls_enabled(True)

    def _apply_template_to_rows(self, rows: List[int], template_name: str, focus_row: Optional[int] = None) -> None:
        # Bulk apply template changes while resetting per-patient overlays.
        template_name = template_name or ""
        template_tasks = self._load_template_tasks(template_name) if template_name else {}
        template_path = self._templates.get(template_name) if template_name else None

        for row_index in rows:
            row = self._queue_model.row_data(row_index)
            if not row:
                continue
            if template_name:
                row[TEMPLATE_KEY] = template_name
                row[TEMPLATE_PATH_KEY] = template_path
                row[TEMPLATE_TASKS_KEY] = self._clone_tasks(template_tasks)
                row[OVERLAY_TASKS_KEY] = self._clone_tasks(template_tasks)
            else:
                row[TEMPLATE_KEY] = ""
                row[TEMPLATE_PATH_KEY] = None
                row[TEMPLATE_TASKS_KEY] = {}
                row[OVERLAY_TASKS_KEY] = {}
            self._queue_model.set_row_data(row_index, row)
        self._refresh_template_controls(force_row=focus_row if focus_row in rows else None)

    def _on_add_structure_clicked(self) -> None:
        row_index = self._current_queue_row()
        row = self._queue_model.row_data(row_index) if row_index is not None else None
        if not row or not row.get(TEMPLATE_KEY):
            return
        patient_id = row.get("patient_id")
        if not patient_id:
            return
        self._pending_overlay_patient_id = patient_id
        self._add_structure_window.show()

    def _on_structures_added(self, structures: List[Tuple[str, str]]) -> None:
        row_index = self._current_queue_row()
        if row_index is None and self._pending_overlay_patient_id:
            row_index = self._queue_model.find_row_by_patient_id(self._pending_overlay_patient_id)
        self._pending_overlay_patient_id = None
        row = self._queue_model.row_data(row_index) if row_index is not None else None
        if not row or not row.get(TEMPLATE_KEY):
            return
        overlay_tasks = row.get(OVERLAY_TASKS_KEY) or {}
        for task_name, structure_name in structures:
            bucket = overlay_tasks.setdefault(task_name, [])
            if structure_name not in bucket:
                bucket.append(structure_name)
        row[OVERLAY_TASKS_KEY] = overlay_tasks
        self._queue_model.set_row_data(row_index, row)
        self._refresh_template_controls()

    def _on_remove_structure_clicked(self) -> None:
        row_index = self._current_queue_row()
        row = self._queue_model.row_data(row_index) if row_index is not None else None
        if not row or not row.get(TEMPLATE_KEY):
            return
        selection = self.TemplStruct.selectionModel()
        if selection is None:
            return
        selected = selection.selectedIndexes()
        if not selected:
            return
        to_remove: set[Tuple[str, str]] = set()
        for index in selected:
            payload = index.data(Qt.ItemDataRole.UserRole)
            display_text = index.data(Qt.ItemDataRole.DisplayRole)
            pair = self._extract_task_structure(payload, display_text)
            if pair:
                to_remove.add(pair)
        if not to_remove:
            return

        overlay_tasks = row.get(OVERLAY_TASKS_KEY) or {}
        for task_name, structure_name in to_remove:
            structures = overlay_tasks.get(task_name, [])
            if structure_name in structures:
                updated = [item for item in structures if item != structure_name]
                if updated:
                    overlay_tasks[task_name] = updated
                else:
                    overlay_tasks.pop(task_name, None)
        row[OVERLAY_TASKS_KEY] = overlay_tasks
        self._queue_model.set_row_data(row_index, row)
        self._refresh_template_controls()

    def _on_reset_to_orig_clicked(self) -> None:
        row_index = self._current_queue_row()
        row = self._queue_model.row_data(row_index) if row_index is not None else None
        if not row or not row.get(TEMPLATE_KEY):
            return
        template_tasks = row.get(TEMPLATE_TASKS_KEY) or {}
        row[OVERLAY_TASKS_KEY] = self._clone_tasks(template_tasks)
        self._queue_model.set_row_data(row_index, row)
        self._refresh_template_controls()

    def _on_save_as_new_clicked(self) -> None:
        row_index = self._current_queue_row()
        row = self._queue_model.row_data(row_index) if row_index is not None else None
        if not row or not row.get(TEMPLATE_KEY):
            return
        patient_id = row.get("patient_id")
        if not patient_id:
            return
        self._pending_save_patient_id = patient_id
        self._saving_template_window.show()

    def _on_template_name_submitted(self, name: str) -> None:
        patient_id = self._pending_save_patient_id
        self._pending_save_patient_id = None
        if not patient_id:
            return
        row_index = self._queue_model.find_row_by_patient_id(patient_id)
        if row_index is None:
            return
        row = self._queue_model.row_data(row_index)
        if not row:
            return
        overlay_tasks = self._clone_tasks(row.get(OVERLAY_TASKS_KEY) or {})

        template_name = self._unique_template_name(name)
        safe_base = self._sanitize_template_filename(template_name)
        self._templates_dir.mkdir(parents=True, exist_ok=True)
        template_path = self._unique_template_path(safe_base)

        save_template(template_path, {"template_name": template_name, "tasks": overlay_tasks})
        self._load_templates()

        row[TEMPLATE_KEY] = template_name
        row[TEMPLATE_PATH_KEY] = template_path
        row[TEMPLATE_TASKS_KEY] = self._clone_tasks(overlay_tasks)
        row[OVERLAY_TASKS_KEY] = self._clone_tasks(overlay_tasks)
        self._queue_model.set_row_data(row_index, row)
        self._refresh_template_controls()

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
        # Keep filenames ASCII + lowercase to honor project constraints.
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
        if not candidate.exists():
            return candidate
        counter = 2
        while True:
            candidate = self._templates_dir / f"{base_name}_{counter}.json"
            if not candidate.exists():
                return candidate
            counter += 1
