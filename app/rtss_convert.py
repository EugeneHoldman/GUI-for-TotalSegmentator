"""NIfTI → RTSTRUCT conversion with explicit raw/postprocessed modes.

Heavy dependencies (SimpleITK, pydicom, numpy, skimage) are imported lazily so
the module can be imported without slowing application startup.

Pipelines:
- Postprocessed (default): binary mask → signed distance field → Gaussian
  smoothing → outward iso-contour at +margin_mm → min-area filter.
- Raw: direct binary contour extraction at threshold 0.5; no smoothing, margin,
  or area-based pruning beyond minimal RTSTRUCT validity.

Public API (kept compatible with existing callers):
- convert_nifti_dir_to_rtss(patient_dir, segmentations_dir, output_rtss_path,
  logger=None, apply_postprocess=True, ...)
- run_postprocess_hook(output_rtss_path, logger=None)  # stub retained
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

# Constants retained from legacy script for behavior parity.
STUDY_COMPONENT_UID = "1.2.840.10008.3.1.2.3.1"
DEFAULT_SMOOTH_SIGMA_MM = 0.8
DEFAULT_MARGIN_MM = 0.4
MIN_CONTOUR_AREA_MM2 = 1.0
MAX_PHYS_ABS_MM = 2000.0


# --------------------------------------------------------------------------- #
# Lightweight logging helpers


def _log(logger, level: str, message: str) -> None:
    """Send a message to provided logger or stdout if absent."""

    if logger is None:
        print(f"{level}: {message}")
        return
    try:
        if level == "INFO" and hasattr(logger, "info"):
            logger.info(message)
        elif level == "WARN" and hasattr(logger, "warn"):
            logger.warn(message)
        elif level == "ERROR" and hasattr(logger, "error"):
            logger.error(message)
        else:
            logger.info(message)
    except Exception:  # pragma: no cover - best-effort fallback
        print(f"{level}: {message}")


def _load_numpy():
    import numpy as np

    return np


def _load_skimage_measure():
    try:
        from skimage import measure as sk_measure

        return sk_measure
    except Exception:
        return None


def _require_dependencies():
    try:
        import SimpleITK  # noqa: F401
        import pydicom  # noqa: F401
    except Exception as exc:  # pragma: no cover - import guard
        raise ImportError("SimpleITK and pydicom are required for RTSS conversion.") from exc


def _format_ds(value) -> str:
    """Format a numeric value as a DICOM DS string."""

    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"DICOM DS value must be finite, got {value!r}")

    def _clean(text: str) -> str:
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return "0" if text in {"-0", "+0", ""} else text

    # DICOM DS is limited to 16 characters; format only at final assignment
    # so internal contour geometry remains full-precision floating point.
    for decimals in range(6, -1, -1):
        text = _clean(f"{numeric:.{decimals}f}")
        if len(text) <= 16:
            return text

    for decimals in range(6, -1, -1):
        mantissa, exponent = f"{numeric:.{decimals}e}".split("e")
        sign = exponent[:1] if exponent[:1] in {"+", "-"} else ""
        digits = exponent[1:] if sign else exponent
        text = f"{_clean(mantissa)}e{sign}{digits.lstrip('0') or '0'}"
        if len(text) <= 16:
            return text

    raise ValueError(f"Could not format {value!r} as a valid DICOM DS value")


# --------------------------------------------------------------------------- #
# DICOM + geometry helpers (lazy imports inside functions)


def load_ct_series_and_uids(ct_dicom_dir: Path):
    """Load the CT series with the most slices and collect per-slice UIDs."""

    import SimpleITK as sitk
    import pydicom

    reader = sitk.ImageSeriesReader()
    series_ids = reader.GetGDCMSeriesIDs(str(ct_dicom_dir))
    if not series_ids:
        raise ValueError(f"No DICOM series found in {ct_dicom_dir}")

    best_series = None
    best_count = -1
    for series_id in series_ids:
        files = reader.GetGDCMSeriesFileNames(str(ct_dicom_dir), series_id)
        if len(files) > best_count:
            best_series = series_id
            best_count = len(files)

    file_names = reader.GetGDCMSeriesFileNames(str(ct_dicom_dir), best_series)
    reader.SetFileNames(file_names)
    ct_img = reader.Execute()

    slice_info_list: List[Dict[str, str]] = []
    first_ds = None
    for path in file_names:
        ds = pydicom.dcmread(path, stop_before_pixels=True, force=True)
        if first_ds is None:
            first_ds = ds
        sop_instance_uid = str(ds.get("SOPInstanceUID", "") or "").strip()
        sop_class_uid = str(ds.get("SOPClassUID", "") or "").strip()
        if not sop_instance_uid or not sop_class_uid:
            raise ValueError(f"Missing SOP UIDs in CT DICOM: {path}")
        slice_info_list.append(
            {
                "sop_instance_uid": sop_instance_uid,
                "sop_class_uid": sop_class_uid,
                "path": path,
            }
        )

    if first_ds is None:
        raise ValueError("Failed to read DICOM metadata from CT series.")

    def _get(ds_obj, tag):
        val = ds_obj.get(tag, "")
        return str(val) if val is not None else ""

    ct_meta = {
        "patient_name": _get(first_ds, "PatientName"),
        "patient_id": _get(first_ds, "PatientID"),
        "patient_birth_date": _get(first_ds, "PatientBirthDate"),
        "patient_sex": _get(first_ds, "PatientSex"),
        "study_instance_uid": _get(first_ds, "StudyInstanceUID"),
        "series_instance_uid": _get(first_ds, "SeriesInstanceUID"),
        "frame_of_reference_uid": _get(first_ds, "FrameOfReferenceUID"),
        "study_date": _get(first_ds, "StudyDate"),
        "study_time": _get(first_ds, "StudyTime"),
        "series_date": _get(first_ds, "SeriesDate"),
        "series_time": _get(first_ds, "SeriesTime"),
        "study_id": _get(first_ds, "StudyID"),
        "accession_number": _get(first_ds, "AccessionNumber"),
        "study_description": _get(first_ds, "StudyDescription"),
        "referring_physician_name": _get(first_ds, "ReferringPhysicianName"),
        "patient_position": _get(first_ds, "PatientPosition"),
        "institution_name": _get(first_ds, "InstitutionName"),
        "manufacturer": _get(first_ds, "Manufacturer"),
        "series_number": _get(first_ds, "SeriesNumber"),
    }

    return ct_img, slice_info_list, ct_meta


def build_rtstruct_skeleton(ct_meta: Dict[str, str], slice_info_list: List[dict]):
    """Create a minimal RTSTRUCT dataset with frame references populated."""

    from datetime import datetime
    import pydicom
    from pydicom.dataset import Dataset
    from pydicom.sequence import Sequence
    from pydicom.uid import (
        ExplicitVRLittleEndian,
        PYDICOM_IMPLEMENTATION_UID,
        RTStructureSetStorage,
        generate_uid,
    )

    pydicom.config.DS_decimal_string_format = "{:.6f}"

    ds = Dataset()
    now = datetime.now()

    ds.SpecificCharacterSet = "ISO_IR 100"
    ds.SOPClassUID = RTStructureSetStorage
    ds.SOPInstanceUID = generate_uid()
    ds.StudyInstanceUID = ct_meta.get("study_instance_uid") or generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.Modality = "RTSTRUCT"
    ds.StructureSetLabel = "RTSTRUCT"
    ds.StructureSetName = "RTSTRUCT"
    ds.StructureSetDate = ct_meta.get("study_date") or now.strftime("%Y%m%d")
    ds.StructureSetTime = ct_meta.get("study_time") or now.strftime("%H%M%S")
    ds.SeriesDate = ct_meta.get("series_date") or ds.StructureSetDate
    ds.SeriesTime = ct_meta.get("series_time") or ds.StructureSetTime
    ds.StudyDate = ct_meta.get("study_date") or ds.StructureSetDate
    ds.StudyTime = ct_meta.get("study_time") or ds.StructureSetTime
    ds.InstanceNumber = "1"
    ds.SeriesNumber = ct_meta.get("series_number") or "1"

    ds.PatientName = ct_meta.get("patient_name")
    ds.PatientID = ct_meta.get("patient_id")
    ds.PatientBirthDate = ct_meta.get("patient_birth_date")
    ds.PatientSex = ct_meta.get("patient_sex")
    ds.StudyID = ct_meta.get("study_id")
    ds.AccessionNumber = ct_meta.get("accession_number")
    ds.StudyDescription = ct_meta.get("study_description")
    ds.ReferringPhysicianName = ct_meta.get("referring_physician_name")
    ds.PatientPosition = ct_meta.get("patient_position")
    ds.InstitutionName = ct_meta.get("institution_name")
    ds.Manufacturer = ct_meta.get("manufacturer")

    frame_uid = ct_meta.get("frame_of_reference_uid") or generate_uid()

    ds.ReferencedFrameOfReferenceSequence = Sequence()
    ref_for = Dataset()
    ref_for.FrameOfReferenceUID = frame_uid
    ref_for.RTReferencedStudySequence = Sequence()
    ref_study = Dataset()
    ref_study.ReferencedSOPClassUID = STUDY_COMPONENT_UID
    ref_study.ReferencedSOPInstanceUID = ds.StudyInstanceUID
    ref_study.RTReferencedSeriesSequence = Sequence()
    ref_series = Dataset()
    ref_series.SeriesInstanceUID = ct_meta.get("series_instance_uid")
    ref_series.ContourImageSequence = Sequence()
    for info in slice_info_list:
        img_ds = Dataset()
        img_ds.ReferencedSOPClassUID = info["sop_class_uid"]
        img_ds.ReferencedSOPInstanceUID = info["sop_instance_uid"]
        ref_series.ContourImageSequence.append(img_ds)
    ref_study.RTReferencedSeriesSequence.append(ref_series)
    ref_for.RTReferencedStudySequence.append(ref_study)
    ds.ReferencedFrameOfReferenceSequence.append(ref_for)

    ds.StructureSetROISequence = Sequence()
    ds.ROIContourSequence = Sequence()
    ds.RTROIObservationsSequence = Sequence()

    file_meta = Dataset()
    file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
    file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = PYDICOM_IMPLEMENTATION_UID
    ds.file_meta = file_meta
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    return ds, frame_uid


def load_nifti_mask(nifti_path: Path):
    """Load a NIfTI mask as a SimpleITK image."""

    import SimpleITK as sitk

    return sitk.ReadImage(str(nifti_path))


def resample_mask_to_ct(mask_img, ct_img):
    """Nearest-neighbor resample of mask onto CT geometry."""

    import SimpleITK as sitk

    mask_bin = sitk.Cast(mask_img > 0, sitk.sitkUInt8)
    return sitk.Resample(
        mask_bin,
        ct_img,
        sitk.Transform(),
        sitk.sitkNearestNeighbor,
        0,
        sitk.sitkUInt8,
    )


def binary_to_sdf(mask_img):
    """Compute signed distance field; inside negative, outside positive."""

    import SimpleITK as sitk

    mask_bin = sitk.Cast(mask_img > 0, sitk.sitkUInt8)
    return sitk.SignedMaurerDistanceMap(
        mask_bin,
        insideIsPositive=False,
        useImageSpacing=True,
        squaredDistance=False,
    )


def smooth_sdf(sdf_img, sigma_mm: float):
    import SimpleITK as sitk

    return sitk.SmoothingRecursiveGaussian(sdf_img, sigma_mm)


def _normalize_contour_rc(contour_rc):
    np = _load_numpy()

    contour_rc = np.asarray(contour_rc, dtype=float)
    if contour_rc.shape[0] < 3:
        return None
    if np.allclose(contour_rc[0], contour_rc[-1], atol=1e-6):
        contour_rc = contour_rc[:-1]
    if contour_rc.shape[0] < 3:
        return None
    return contour_rc


def _marching_squares_contours(arr2d, level: float):
    """Lightweight marching squares fallback when skimage is unavailable."""

    np = _load_numpy()

    h, w = arr2d.shape
    segments = []

    case_to_edges = {
        0: [],
        1: [(3, 0)],
        2: [(0, 1)],
        3: [(3, 1)],
        4: [(1, 2)],
        5: [(3, 0), (1, 2)],
        6: [(0, 2)],
        7: [(3, 2)],
        8: [(2, 3)],
        9: [(0, 2)],
        10: [(0, 1), (2, 3)],
        11: [(1, 2)],
        12: [(1, 3)],
        13: [(0, 1)],
        14: [(0, 3)],
        15: [],
    }

    def _interp(p0, p1, v0, v1):
        if v0 == v1:
            t = 0.5
        else:
            t = (level - v0) / (v1 - v0)
            t = max(0.0, min(1.0, t))
        r = p0[0] + t * (p1[0] - p0[0])
        c = p0[1] + t * (p1[1] - p0[1])
        return (r, c)

    for i in range(h - 1):
        for j in range(w - 1):
            v_tl = arr2d[i, j]
            v_tr = arr2d[i, j + 1]
            v_br = arr2d[i + 1, j + 1]
            v_bl = arr2d[i + 1, j]
            if not np.isfinite([v_tl, v_tr, v_br, v_bl]).all():
                continue

            case = 0
            if v_tl >= level:
                case |= 1
            if v_tr >= level:
                case |= 2
            if v_br >= level:
                case |= 4
            if v_bl >= level:
                case |= 8

            edges = case_to_edges[case]
            if not edges:
                continue

            corners = {
                0: ((i, j), v_tl),
                1: ((i, j + 1), v_tr),
                2: ((i + 1, j + 1), v_br),
                3: ((i + 1, j), v_bl),
            }
            edge_points = {
                0: (corners[0], corners[1]),
                1: (corners[1], corners[2]),
                2: (corners[3], corners[2]),
                3: (corners[0], corners[3]),
            }

            for e0, e1 in edges:
                (p0, v0), (p1, v1) = edge_points[e0]
                (p2, v2), (p3, v3) = edge_points[e1]
                q0 = _interp(p0, p1, v0, v1)
                q1 = _interp(p2, p3, v2, v3)
                segments.append((q0, q1))

    return _stitch_segments(segments)


def _stitch_segments(segments, tol: float = 1e-5):
    np = _load_numpy()

    if not segments:
        return []

    def key(pt):
        return (round(pt[0] / tol) * tol, round(pt[1] / tol) * tol)

    adjacency = {}
    for idx, (p0, p1) in enumerate(segments):
        adjacency.setdefault(key(p0), []).append((idx, 0))
        adjacency.setdefault(key(p1), []).append((idx, 1))

    visited = set()
    contours = []

    for idx, (p0, p1) in enumerate(segments):
        if idx in visited:
            continue
        visited.add(idx)
        poly = [p0, p1]

        _extend_polyline(poly, adjacency, segments, visited, at_start=False, key_func=key)
        _extend_polyline(poly, adjacency, segments, visited, at_start=True, key_func=key)

        contours.append(np.array(poly, dtype=float))

    return contours


def _extend_polyline(poly, adjacency, segments, visited, at_start, key_func):
    while True:
        pt = poly[0] if at_start else poly[-1]
        neighbors = adjacency.get(key_func(pt), [])
        next_seg = None
        for seg_idx, endpoint in neighbors:
            if seg_idx in visited:
                continue
            next_seg = (seg_idx, endpoint)
            break
        if next_seg is None:
            break
        seg_idx, endpoint = next_seg
        visited.add(seg_idx)
        s0, s1 = segments[seg_idx]
        other = s1 if endpoint == 0 else s0
        if at_start:
            poly.insert(0, other)
        else:
            poly.append(other)


def _find_contours(arr2d, level: float):
    sk_measure = _load_skimage_measure()
    if sk_measure is not None:
        return sk_measure.find_contours(arr2d, level=level)
    return _marching_squares_contours(arr2d, level)


def contour_rc_to_phys(contour_rc, slice_k: int, ct_img):
    np = _load_numpy()

    pts = []
    for r, c in contour_rc:
        phys = ct_img.TransformContinuousIndexToPhysicalPoint((float(c), float(r), float(slice_k)))
        if not np.isfinite(phys).all():
            return None
        if max(abs(phys[0]), abs(phys[1]), abs(phys[2])) > MAX_PHYS_ABS_MM:
            return None
        pts.append(phys)
    pts = np.array(pts, dtype=float)
    # Flatten slice jitter by enforcing constant Z per contour.
    z_med = float(np.median(pts[:, 2]))
    pts[:, 2] = z_med
    return pts


def polygon_area_xy(points_xyz) -> float:
    np = _load_numpy()

    x = points_xyz[:, 0]
    y = points_xyz[:, 1]
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def extract_contours_from_sdf_level(sdf_img, ct_img, level: float, min_contour_area_mm2: float):
    """Extract contours from an SDF image at the given iso-level."""

    import SimpleITK as sitk

    np = _load_numpy()
    sdf_arr = sitk.GetArrayFromImage(sdf_img)  # (z, y, x)

    points_per_slice: Dict[int, List] = {}
    contour_points_counts: List[int] = []

    depth = sdf_arr.shape[0]
    for k in range(depth):
        slice_arr = sdf_arr[k]
        min_val = np.nanmin(slice_arr)
        max_val = np.nanmax(slice_arr)
        if level < min_val or level > max_val:
            continue
        contours = _find_contours(slice_arr, level=level)
        if not contours:
            continue
        for contour in contours:
            contour = _normalize_contour_rc(contour)
            if contour is None:
                continue
            pts = contour_rc_to_phys(contour, k, ct_img)
            if pts is None:
                continue
            area = polygon_area_xy(pts)
            if area < min_contour_area_mm2:
                continue
            points_per_slice.setdefault(k, []).append(pts)
            contour_points_counts.append(len(pts))

    return points_per_slice, contour_points_counts


def extract_contours_from_binary(mask_img, ct_img, threshold: float = 0.5):
    """Direct binary contour extraction without smoothing/margin."""

    import SimpleITK as sitk

    np = _load_numpy()
    mask_arr = sitk.GetArrayFromImage(mask_img)  # (z, y, x)

    points_per_slice: Dict[int, List] = {}
    contour_points_counts: List[int] = []

    depth = mask_arr.shape[0]
    for k in range(depth):
        slice_arr = mask_arr[k]
        if np.sum(slice_arr > threshold) == 0:
            continue
        contours = _find_contours(slice_arr, level=threshold)
        if not contours:
            continue
        for contour in contours:
            contour = _normalize_contour_rc(contour)
            if contour is None:
                continue
            pts = contour_rc_to_phys(contour, k, ct_img)
            if pts is None:
                continue
            points_per_slice.setdefault(k, []).append(pts)
            contour_points_counts.append(len(pts))

    return points_per_slice, contour_points_counts


def _roi_display_color(roi_number: int):
    palette = [
        [255, 0, 0],
        [0, 255, 0],
        [0, 128, 255],
        [255, 128, 0],
        [255, 0, 255],
        [0, 255, 255],
        [255, 255, 0],
        [128, 0, 255],
        [0, 128, 0],
        [255, 192, 203],
    ]
    return palette[(roi_number - 1) % len(palette)]


def add_roi_to_rtstruct(
    ds, roi_name: str, points_per_slice: Dict[int, List], slice_info_list: List[dict], roi_number: int, frame_uid: str
):
    import pydicom
    from pydicom.dataset import Dataset
    from pydicom.sequence import Sequence

    roi_ds = Dataset()
    roi_ds.ROINumber = roi_number
    roi_ds.ReferencedFrameOfReferenceUID = frame_uid
    roi_ds.ROIName = roi_name
    roi_ds.ROIGenerationAlgorithm = "AUTOMATIC"
    ds.StructureSetROISequence.append(roi_ds)

    roi_contour = Dataset()
    roi_contour.ReferencedROINumber = roi_number
    roi_contour.ROIDisplayColor = _roi_display_color(roi_number)
    roi_contour.ContourSequence = Sequence()

    for slice_k in sorted(points_per_slice.keys()):
        if slice_k >= len(slice_info_list):
            continue
        contours = points_per_slice[slice_k]
        for pts_xyz in contours:
            contour_ds = Dataset()
            contour_ds.ContourGeometricType = "CLOSED_PLANAR"
            contour_ds.NumberOfContourPoints = int(len(pts_xyz))
            contour_ds.ContourData = [_format_ds(v) for v in pts_xyz.reshape(-1)]
            contour_ds.ContourImageSequence = Sequence()
            img_ref = Dataset()
            img_ref.ReferencedSOPClassUID = slice_info_list[slice_k]["sop_class_uid"]
            img_ref.ReferencedSOPInstanceUID = slice_info_list[slice_k]["sop_instance_uid"]
            contour_ds.ContourImageSequence.append(img_ref)
            roi_contour.ContourSequence.append(contour_ds)

    ds.ROIContourSequence.append(roi_contour)

    obs = Dataset()
    obs.ObservationNumber = roi_number
    obs.ReferencedROINumber = roi_number
    obs.RTROIInterpretedType = "ORGAN"
    obs.ROIInterpreter = ""
    ds.RTROIObservationsSequence.append(obs)


def write_rtss(ds, output_rtss_path: Path):
    import pydicom

    pydicom.dcmwrite(str(output_rtss_path), ds, write_like_original=False)


# --------------------------------------------------------------------------- #
# Main conversion entry point


def convert_nifti_dir_to_rtss(
    patient_dir: Path,
    segmentations_dir: Path,
    output_rtss_path: Path,
    logger=None,
    apply_postprocess: bool = True,
    sigma_mm: float = DEFAULT_SMOOTH_SIGMA_MM,
    margin_mm: float = DEFAULT_MARGIN_MM,
    min_contour_area_mm2: float = MIN_CONTOUR_AREA_MM2,
) -> Tuple[int, int, int]:
    """Convert NIfTI masks under `segmentations_dir` into a single RTSTRUCT.

    Returns (written, skipped_empty, missing).
    - written: ROIs successfully written
    - skipped_empty: masks with no voxels/contours after processing
    - missing: reserved (always 0) for compatibility
    """

    _require_dependencies()
    import SimpleITK as sitk

    patient_dir = Path(patient_dir)
    segmentations_dir = Path(segmentations_dir)
    output_rtss_path = Path(output_rtss_path)

    if not patient_dir.exists() or not patient_dir.is_dir():
        raise ValueError(f"Patient folder not found: {patient_dir}")
    if not segmentations_dir.exists() or not segmentations_dir.is_dir():
        raise ValueError(f"Segmentations folder not found: {segmentations_dir}")

    ct_img, slice_info_list, ct_meta = load_ct_series_and_uids(patient_dir)
    if not ct_meta.get("study_instance_uid"):
        raise ValueError("CT StudyInstanceUID missing; cannot build RTSTRUCT.")
    if not ct_meta.get("series_instance_uid"):
        raise ValueError("CT SeriesInstanceUID missing; cannot build RTSTRUCT.")
    if not ct_meta.get("frame_of_reference_uid"):
        raise ValueError("CT FrameOfReferenceUID missing; cannot build RTSTRUCT.")

    nifti_files = sorted(segmentations_dir.glob("*.nii")) + sorted(
        segmentations_dir.glob("*.nii.gz")
    )
    if not nifti_files:
        raise ValueError(f"No NIfTI files found in {segmentations_dir}")

    if not apply_postprocess:
        if (
            sigma_mm != DEFAULT_SMOOTH_SIGMA_MM
            or margin_mm != DEFAULT_MARGIN_MM
            or min_contour_area_mm2 != MIN_CONTOUR_AREA_MM2
        ):
            _log(
                logger,
                "WARN",
                "Postprocess disabled: sigma/margin/min_area parameters ignored to preserve raw geometry.",
            )

    ds, frame_uid = build_rtstruct_skeleton(ct_meta, slice_info_list)

    processed = 0
    skipped_empty = 0
    missing = 0
    roi_number = 1

    stats_filter = sitk.StatisticsImageFilter()

    for nifti_path in nifti_files:
        roi_name = nifti_path.stem
        if roi_name.endswith(".nii"):
            roi_name = roi_name[:-4]

        mask_img = load_nifti_mask(nifti_path)
        mask_ct = resample_mask_to_ct(mask_img, ct_img)

        stats_filter.Execute(mask_ct)
        if stats_filter.GetSum() == 0:
            skipped_empty += 1
            continue

        if apply_postprocess:
            sdf_img = binary_to_sdf(mask_ct)
            sdf_img = smooth_sdf(sdf_img, sigma_mm)
            points_per_slice, _ = extract_contours_from_sdf_level(
                sdf_img,
                ct_img,
                level=margin_mm,
                min_contour_area_mm2=min_contour_area_mm2,
            )
        else:
            points_per_slice, _ = extract_contours_from_binary(
                mask_ct,
                ct_img,
                threshold=0.5,
            )

        if not points_per_slice:
            skipped_empty += 1
            continue

        add_roi_to_rtstruct(
            ds=ds,
            roi_name=roi_name,
            points_per_slice=points_per_slice,
            slice_info_list=slice_info_list,
            roi_number=roi_number,
            frame_uid=frame_uid,
        )
        processed += 1
        roi_number += 1

    if processed == 0:
        raise ValueError("No RTSTRUCT ROIs were generated from the provided masks.")

    output_rtss_path.parent.mkdir(parents=True, exist_ok=True)
    write_rtss(ds, output_rtss_path)

    return processed, skipped_empty, missing


def run_postprocess_hook(output_rtss_path: Path, logger=None) -> Tuple[bool, str | None]:
    """Compatibility stub invoked after conversion when postproc is enabled.

    The actual smoothing/margin pipeline runs inside convert_nifti_dir_to_rtss
    when apply_postprocess=True. This hook simply reports success.
    """

    return True, None


# --------------------------------------------------------------------------- #
# CLI support (optional direct use)


def _parse_args(argv: Iterable[str]):
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert NIfTI masks to RTSTRUCT (raw or postprocessed)."
    )
    parser.add_argument("--ct_dicom_dir", required=True, help="Path to CT DICOM folder.")
    parser.add_argument("--seg_dir", required=True, help="Path to NIfTI segmentations folder.")
    parser.add_argument("--out_rtss", required=True, help="Output RTSTRUCT path.")
    parser.add_argument(
        "--postprocess",
        choices=["on", "off"],
        default="on",
        help="Apply SDF smoothing + margin (on) or use raw contours (off). Default: on.",
    )
    parser.add_argument("--sigma_mm", type=float, default=DEFAULT_SMOOTH_SIGMA_MM)
    parser.add_argument("--margin_mm", type=float, default=DEFAULT_MARGIN_MM)
    parser.add_argument("--min_contour_area_mm2", type=float, default=MIN_CONTOUR_AREA_MM2)
    return parser.parse_args(list(argv))


def main(argv: Iterable[str] | None = None) -> int:
    import sys
    from traceback import format_exc

    args = _parse_args(argv or sys.argv[1:])
    apply_postprocess = args.postprocess == "on"
    try:
        written, skipped_empty, missing = convert_nifti_dir_to_rtss(
            patient_dir=Path(args.ct_dicom_dir),
            segmentations_dir=Path(args.seg_dir),
            output_rtss_path=Path(args.out_rtss),
            logger=None,
            apply_postprocess=apply_postprocess,
            sigma_mm=args.sigma_mm,
            margin_mm=args.margin_mm,
            min_contour_area_mm2=args.min_contour_area_mm2,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        print(format_exc(), file=sys.stderr)
        return 1

    print(f"RTSTRUCT written: {written}, skipped empty: {skipped_empty}, missing: {missing}.")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
