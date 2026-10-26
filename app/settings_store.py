"""Simple JSON-backed settings store.

Avoids heavy dependencies; uses stdlib only.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class SettingsStore:
    """Read and write settings in a small JSON file."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def load(self) -> Dict[str, Any]:
        """Return stored settings or an empty dict on error."""
        if not self._path.exists():
            return {}
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, dict):
                return data
        except (OSError, json.JSONDecodeError):
            return {}
        return {}

    def save(self, data: Dict[str, Any]) -> None:
        """Persist settings to disk."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
