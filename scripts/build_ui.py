"""Compile Qt Designer .ui files into Python modules."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def _compile_ui(ui_path: Path, output_path: Path) -> None:
    try:
        subprocess.run(
            ["pyside6-uic", str(ui_path), "-o", str(output_path)],
            check=True,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pyside6-uic not found on PATH. Install PySide6 or activate the env."
        ) from exc


def main() -> int:
    base_dir = Path(__file__).resolve().parents[1]
    ui_src_dir = base_dir / "assets" / "ui_src"
    out_dir = base_dir / "ui_generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    init_path = out_dir / "__init__.py"
    init_path.touch(exist_ok=True)

    ui_files = sorted(ui_src_dir.glob("*.ui"))
    if not ui_files:
        print(f"No .ui files found in {ui_src_dir}", file=sys.stderr)
        return 1

    for ui_path in ui_files:
        out_name = f"ui_{ui_path.stem}.py"
        output_path = out_dir / out_name
        _compile_ui(ui_path, output_path)
        print(f"Built {output_path.relative_to(base_dir)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
