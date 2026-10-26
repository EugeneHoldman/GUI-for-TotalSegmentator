"""Patient folder scanning helpers with deterministic, depth-limited search and session caching."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

MAX_SCAN_DEPTH = 3


@dataclass(frozen=True)
class FileInfo:
    """Lightweight record about a file within a patient folder."""

    path: Path
    rel_path: Path
    size: int
    mtime_ns: int
    is_dicom_candidate: bool
    is_rtss_name: bool
    is_nifti_in_segmentations: bool


_PATIENT_CACHE: Dict[Path, Dict[str, object]] = {}


def _format_patient_name(raw_name: object) -> str:
    if raw_name is None:
        return ""
    name = str(raw_name).strip()
    if not name:
        return ""
    parts = [part.strip() for part in name.split("^") if part.strip()]
    if len(parts) >= 2:
        family = parts[0]
        given = " ".join(parts[1:])
        return f"{given}, {family}" if given else family
    return name.replace("^", " ").strip()


def _iter_files_within_depth(root: Path, max_depth: int = MAX_SCAN_DEPTH):
    """Yield files within a depth limit, in deterministic order."""
    try:
        entries = sorted(root.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return
    for entry in entries:
        if entry.is_file():
            yield entry
    for entry in entries:
        if entry.is_dir() and max_depth > 0:
            yield from _iter_files_within_depth(entry, max_depth - 1)


def _is_rtss_name(path: Path) -> bool:
    return path.name.lower().startswith("rtss")


def _is_dicom_candidate(path: Path, is_rtss_name: bool) -> bool:
    """Apply candidate rule: is_dicom first, then .dcm suffix, always accept rtss*."""
    try:
        from pydicom.misc import is_dicom

        if is_dicom(str(path)):
            return True
    except Exception:
        # Fall back to suffix/rtss checks when detection fails.
        pass
    if path.suffix.lower() == ".dcm":
        return True
    return is_rtss_name


def _collect_file_infos(patient_dir: Path) -> Tuple[List[FileInfo], Tuple[Tuple[str, int, int], ...]]:
    """Collect file metadata for signature + later scans without reading DICOM headers."""
    file_infos: List[FileInfo] = []
    signature_entries: List[Tuple[str, int, int]] = []

    for path in _iter_files_within_depth(patient_dir, MAX_SCAN_DEPTH):
        try:
            stat = path.stat()
        except OSError:
            continue
        size = int(stat.st_size)
        mtime_ns = int(stat.st_mtime_ns)
        rel_path = path.relative_to(patient_dir)

        rtss_name = _is_rtss_name(path)
        nifti_in_seg = path.parent.name.lower() == "segmentations" and (
            path.name.lower().endswith(".nii") or path.name.lower().endswith(".nii.gz")
        )
        dicom_candidate = _is_dicom_candidate(path, rtss_name)

        info = FileInfo(
            path=path,
            rel_path=rel_path,
            size=size,
            mtime_ns=mtime_ns,
            is_dicom_candidate=dicom_candidate,
            is_rtss_name=rtss_name,
            is_nifti_in_segmentations=nifti_in_seg,
        )
        file_infos.append(info)

        # Signature tracks all files within scope to detect additions/removals that might
        # affect candidacy on subsequent rescans.
        signature_entries.append((rel_path.as_posix(), size, mtime_ns))

    signature = tuple(sorted(signature_entries))
    return file_infos, signature


def _read_dicom_dataset(dcm_path: Path):
    """Read a DICOM dataset with minimal overhead."""
    import pydicom

    try:
        return pydicom.dcmread(str(dcm_path), stop_before_pixels=True, force=True)
    except Exception:
        return None


def _extract_patient_id(dataset) -> str:
    raw = getattr(dataset, "PatientID", None)
    if raw is None:
        return ""
    return str(raw).strip()


def _find_first_ct(
    dicom_candidates: List[FileInfo],
) -> Tuple[Optional[object], Optional[Path]]:
    """Return (dataset, path) for the first confirmed CT using size-ascending order."""
    for info in sorted(dicom_candidates, key=lambda item: item.size):
        dataset = _read_dicom_dataset(info.path)
        modality = getattr(dataset, "Modality", None) if dataset is not None else None
        if dataset is not None and str(modality).upper() == "CT":
            return dataset, info.path
    return None, None


def _find_rtss_in_dir(
    rtss_candidates: List[FileInfo],
    target_dir: Path,
) -> Tuple[bool, Optional[object]]:
    """Search for RTSTRUCT within a specific directory."""
    for info in sorted(rtss_candidates, key=lambda item: item.size):
        if info.path.parent != target_dir:
            continue
        dataset = _read_dicom_dataset(info.path)
        modality = getattr(dataset, "Modality", None) if dataset is not None else None
        if dataset is not None and str(modality).upper() == "RTSTRUCT":
            return True, dataset
    return False, None


def _find_rtss_any(rtss_candidates: List[FileInfo]) -> Tuple[bool, Optional[object], Optional[Path]]:
    """Search for RTSTRUCT anywhere within the patient scope."""
    for info in sorted(rtss_candidates, key=lambda item: item.size):
        dataset = _read_dicom_dataset(info.path)
        modality = getattr(dataset, "Modality", None) if dataset is not None else None
        if dataset is not None and str(modality).upper() == "RTSTRUCT":
            return True, dataset, info.path.parent
    return False, None, None


def _has_nifti_in_segmentations(ct_dir: Path, file_infos: List[FileInfo]) -> bool:
    seg_dir = ct_dir / "segmentations"
    for info in file_infos:
        if info.is_nifti_in_segmentations and info.path.parent == seg_dir:
            return True
    return False


def _build_row(
    patient_id: str,
    name: str,
    has_ct: bool,
    has_nifti: bool,
    has_rtss: bool,
    patient_dir: Path,
    scan_dir: Path,
) -> dict:
    return {
        "patient_id": patient_id,
        "name": name,
        "has_ct": has_ct,
        "has_nifti": has_nifti,
        "has_rtss": has_rtss,
        # Keep real filesystem paths separate from DICOM metadata.
        "patient_dir": str(patient_dir),
        "scan_dir": str(scan_dir),
    }


def _scan_patient(patient_dir: Path, file_infos: List[FileInfo]) -> Optional[dict]:
    """Apply CT/RTSS rules to decide if a patient row should be emitted."""
    dicom_candidates = [info for info in file_infos if info.is_dicom_candidate]
    rtss_candidates = [info for info in file_infos if info.is_rtss_name]

    ct_dataset, ct_path = _find_first_ct(dicom_candidates)
    has_ct = ct_dataset is not None
    has_rtss = False
    has_nifti = False
    demographics_source = None
    scan_dir = patient_dir

    if has_ct and ct_path:
        ct_dir = ct_path.parent
        scan_dir = ct_dir
        has_rtss, _ = _find_rtss_in_dir(rtss_candidates, ct_dir)
        has_nifti = _has_nifti_in_segmentations(ct_dir, file_infos)
        demographics_source = ct_dataset
    else:
        has_rtss, rtss_dataset, rtss_dir = _find_rtss_any(rtss_candidates)
        if not has_rtss:
            return None
        demographics_source = rtss_dataset
        if rtss_dir is not None:
            scan_dir = rtss_dir

    if demographics_source is None:
        return None

    patient_id = _extract_patient_id(demographics_source)
    patient_name = _format_patient_name(getattr(demographics_source, "PatientName", None))
    if not patient_id or not patient_name:
        return None

    return _build_row(
        patient_id=patient_id,
        name=patient_name,
        has_ct=has_ct,
        has_nifti=has_nifti if has_ct else False,
        has_rtss=has_rtss,
        patient_dir=patient_dir,
        scan_dir=scan_dir,
    )


def scan_patients(patients_root: Path, *, force_rescan: bool = False) -> List[dict]:
    """Scan patient folders under patients_root using a signature cache.

    force_rescan=True clears the session cache so every patient is re-evaluated.
    """
    patients_root = Path(patients_root)
    if not patients_root.exists() or not patients_root.is_dir():
        return []

    if force_rescan:
        _PATIENT_CACHE.clear()

    patient_dirs = [child for child in sorted(patients_root.iterdir(), key=lambda p: p.name.lower()) if child.is_dir()]

    results: List[dict] = []
    new_cache: Dict[Path, Dict[str, object]] = {}

    for patient_dir in patient_dirs:
        file_infos, signature = _collect_file_infos(patient_dir)
        cached = _PATIENT_CACHE.get(patient_dir)

        if cached and cached.get("signature") == signature:
            row = cached.get("row")
        else:
            row = _scan_patient(patient_dir, file_infos)

        new_cache[patient_dir] = {"signature": signature, "row": row}
        if row:
            results.append(row)

    _PATIENT_CACHE.clear()
    _PATIENT_CACHE.update(new_cache)
    return results
