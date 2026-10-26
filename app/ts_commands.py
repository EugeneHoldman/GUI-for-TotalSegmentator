"""TotalSegmentator command helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

TOTAL_TASK_NAME = "total"
COMBINED_ORGANS_TASK_NAME = "combined_organs"
DEFAULT_TS_EXECUTABLE = "TotalSegmentator"
DEFAULT_COMBINE_MASKS_EXECUTABLE = "totalseg_combine_masks"

# Synthetic Combined_organs classes are built from Total roi_subset outputs.
COMBINED_ORGANS_ROI_SUBSETS: Dict[str, Tuple[str, ...]] = {
    "lung_left": (
        "lung_upper_lobe_left",
        "lung_lower_lobe_left",
    ),
    "lung_right": (
        "lung_upper_lobe_right",
        "lung_middle_lobe_right",
        "lung_lower_lobe_right",
    ),
}


def _canonical_name(name: str) -> str:
    """Normalize task/structure tokens to lowercase snake_case."""
    canonical = name.strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in canonical:
        canonical = canonical.replace("__", "_")
    return canonical


def _normalize_task_list(structures: Iterable[object]) -> List[str]:
    seen: set[str] = set()
    cleaned: List[str] = []
    for item in structures:
        if not isinstance(item, str):
            continue
        name = item.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        cleaned.append(name)
    return cleaned


def load_task_definitions(path: Path) -> Dict[str, List[str]]:
    """Load task -> structure list mapping from totalsegmentator.json."""
    path = Path(path)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    if isinstance(data, dict) and isinstance(data.get("tasks"), dict):
        raw_tasks = data["tasks"]
    elif isinstance(data, dict):
        raw_tasks = data
    else:
        return {}

    tasks: Dict[str, List[str]] = {}
    for task_name, structures in raw_tasks.items():
        if not isinstance(task_name, str) or not isinstance(structures, list):
            continue
        cleaned = _normalize_task_list(structures)
        if cleaned:
            tasks[task_name] = cleaned
    return tasks


def resolve_task_structures(task_definitions: Dict[str, List[str]], task_name: str) -> List[str] | None:
    """Return structures for a task name (case-insensitive), if known."""
    if task_name in task_definitions:
        return task_definitions[task_name]
    lowered = task_name.lower()
    canonical = _canonical_name(task_name)
    for name, structures in task_definitions.items():
        if name.lower() == lowered or _canonical_name(name) == canonical:
            return structures
    return None


def normalize_structure_list(structures: Iterable[object]) -> List[str]:
    """Normalize a structure list to a unique list of strings."""
    return _normalize_task_list(structures)


def is_total_task(task_name: str) -> bool:
    return _canonical_name(task_name) == TOTAL_TASK_NAME


def is_combined_organs_task(task_name: str) -> bool:
    return _canonical_name(task_name) == COMBINED_ORGANS_TASK_NAME


def resolve_combined_organs_sources(structure_name: str) -> tuple[str, List[str]] | None:
    """Resolve a Combined_organs class into (mask_name, total_roi_subset)."""
    mask_name = _canonical_name(structure_name)
    sources = COMBINED_ORGANS_ROI_SUBSETS.get(mask_name)
    if not sources:
        return None
    return mask_name, list(sources)


def is_total_all(selected: Iterable[str], total_structures: Iterable[str]) -> bool:
    selected_set = {name.strip().lower() for name in selected if isinstance(name, str)}
    total_set = {name.strip().lower() for name in total_structures if isinstance(name, str)}
    return bool(selected_set) and selected_set == total_set


def resolve_command_binaries(options: Dict[str, object] | None = None) -> Tuple[str, str]:
    """Resolve command executables based on installation settings."""
    if not isinstance(options, dict):
        return DEFAULT_TS_EXECUTABLE, DEFAULT_COMBINE_MASKS_EXECUTABLE
    use_conda = bool(options.get("use_conda"))
    conda_env_path = options.get("conda_env_path")
    if not use_conda or not isinstance(conda_env_path, str):
        return DEFAULT_TS_EXECUTABLE, DEFAULT_COMBINE_MASKS_EXECUTABLE
    env_text = conda_env_path.strip()
    if not env_text:
        return DEFAULT_TS_EXECUTABLE, DEFAULT_COMBINE_MASKS_EXECUTABLE
    env_path = Path(env_text)
    return (
        str(env_path / "Scripts" / "TotalSegmentator.exe"),
        str(env_path / "Scripts" / "totalseg_combine_masks.exe"),
    )


def build_total_command(
    input_dir: Path,
    roi_subset: Iterable[str] | None = None,
    executable: str = DEFAULT_TS_EXECUTABLE,
) -> List[str]:
    """Build a TotalSegmentator command for the Total task."""
    # Explicitly write outputs into the CT folder to keep NIfTI beside source DICOMs.
    segmentations_dir = Path(input_dir) / "segmentations"
    cmd = [executable, "-i", str(input_dir), "-o", str(segmentations_dir)]
    if roi_subset:
        cmd.extend(["--roi_subset", *list(roi_subset), "--robust_crop"])
    cmd.extend(["--nr_thr_saving", "1"])
    return cmd


def build_task_command(
    input_dir: Path,
    task_name: str,
    executable: str = DEFAULT_TS_EXECUTABLE,
) -> List[str]:
    """Build a TotalSegmentator command for a named task."""
    segmentations_dir = Path(input_dir) / "segmentations"
    return [
        executable,
        "-i",
        str(input_dir),
        "-o",
        str(segmentations_dir),
        "-ta",
        task_name,
        "--nr_thr_saving",
        "1",
    ]


def build_combine_masks_command(
    segmentations_dir: Path,
    output_filename: str,
    mask_name: str,
    executable: str = DEFAULT_COMBINE_MASKS_EXECUTABLE,
) -> List[str]:
    """Build a totalseg_combine_masks command for one synthetic combined mask."""
    output_path = Path(segmentations_dir) / output_filename
    return [
        executable,
        "-i",
        str(segmentations_dir),
        "-o",
        str(output_path),
        "-m",
        mask_name,
    ]
