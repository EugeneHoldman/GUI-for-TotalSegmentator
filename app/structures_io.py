"""Read and write structures.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def load_structures(path: Path) -> Dict[str, Any]:
    """Load structures.json or return an empty dict on error."""
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data
    except (OSError, json.JSONDecodeError):
        return {}
    return {}


def save_structures(path: Path, data: Dict[str, Any]) -> None:
    """Save structures.json to disk."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
