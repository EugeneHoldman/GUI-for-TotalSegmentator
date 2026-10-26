"""Template file helpers.

Avoid parsing large JSON files during startup.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def list_templates(templates_dir: Path) -> List[Dict[str, object]]:
    """List user templates without parsing system JSON files.

    Only parse JSON files that advertise a "template_name" in the prefix.
    """
    templates_dir = Path(templates_dir)
    if not templates_dir.exists():
        return []

    skip_filenames = {"totalsegmentator.json", "structures.json"}
    results: List[Dict[str, object]] = []
    for path in templates_dir.iterdir():
        if path.suffix.lower() != ".json":
            continue
        if path.name.lower() in skip_filenames:
            continue
        try:
            with path.open("r", encoding="utf-8") as handle:
                prefix = handle.read(2048)
            if '"template_name"' not in prefix:
                continue
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            template_name = data.get("template_name")
            if template_name:
                results.append({"name": template_name, "path": path})
        except (OSError, json.JSONDecodeError):
            continue
    return results


def load_template(path: Path) -> Dict[str, object]:
    """Load a template JSON file."""
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_template(path: Path, data: Dict[str, object]) -> None:
    """Save a template JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
