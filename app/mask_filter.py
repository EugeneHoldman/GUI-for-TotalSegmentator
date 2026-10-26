"""Mask filtering helpers for non-Total tasks."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple


def _mask_base_name(filename: str) -> str | None:
    lowered = filename.lower()
    if lowered.endswith(".nii.gz"):
        return lowered[:-7]
    if lowered.endswith(".nii"):
        return lowered[:-4]
    return None


def remove_unwanted_masks(
    segmentations_dir: Path,
    keep_names: Iterable[str],
    only_names: Iterable[str] | None = None,
) -> Tuple[int, int]:
    """Remove NIfTI masks not in keep_names and return (removed, kept)."""
    segmentations_dir = Path(segmentations_dir)
    keep_set = {name.strip().lower() for name in keep_names if isinstance(name, str)}
    only_set = None
    if only_names is not None:
        only_set = {name.strip().lower() for name in only_names if isinstance(name, str)}

    removed = 0
    kept = 0
    if not segmentations_dir.exists():
        return removed, kept

    try:
        for path in segmentations_dir.iterdir():
            if not path.is_file():
                continue
            base = _mask_base_name(path.name)
            if base is None:
                continue
            if only_set is not None and base not in only_set:
                continue
            if base in keep_set:
                kept += 1
                continue
            try:
                path.unlink()
                removed += 1
            except OSError:
                continue
    except OSError:
        return removed, kept
    return removed, kept
