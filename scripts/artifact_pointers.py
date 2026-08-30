"""Snapshot and restore published processed-artifact pointers."""

from __future__ import annotations

import os
from pathlib import Path


def snapshot_pointers(root: Path) -> dict[Path, bytes]:
    return {
        path: path.read_bytes()
        for path in (root / "data" / "processed").glob("**/latest.json")
    }


def restore_pointers(root: Path, before: dict[Path, bytes]) -> None:
    current = set((root / "data" / "processed").glob("**/latest.json"))
    for path in current - set(before):
        path.unlink()
    for path, content in before.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".rollback.tmp")
        temporary.write_bytes(content)
        os.replace(temporary, path)
