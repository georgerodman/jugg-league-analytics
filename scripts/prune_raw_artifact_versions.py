#!/usr/bin/env python3
"""Remove superseded timestamped raw snapshots while preserving latest builds."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DEFAULT_AUDIT = ROOT / ".local" / "audits" / "repository-artifacts.json"
DEFAULT_MANIFEST = ROOT / ".local" / "audits" / "raw-prune-candidates.json"
BUILD_PATTERN = re.compile(r"^(?:\d{8}T\d{6}Z|[0-9a-f]{16})$")


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def keep_paths(audit: dict[str, Any]) -> set[str]:
    kept: set[str] = set()
    for group in ("runtime", "tests", "published"):
        kept.update(item["path"] for item in audit[group]["files"])
    return kept


def belongs_to_pointer_managed_build(path: Path) -> bool:
    build_directories = [parent for parent in path.parents if BUILD_PATTERN.fullmatch(parent.name)]
    for build in build_directories:
        for ancestor in build.parents:
            if ancestor == RAW.parent:
                break
            if (ancestor / "latest.json").is_file():
                return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    audit = json.loads(args.audit.read_text(encoding="utf-8"))
    missing = [path for paths in audit["missing"].values() for path in paths]
    if missing:
        raise RuntimeError(f"Artifact audit has missing dependencies: {', '.join(missing)}")
    kept = keep_paths(audit)
    files = [
        path
        for path in sorted(RAW.rglob("*"))
        if path.is_file()
        and belongs_to_pointer_managed_build(path)
        and str(path.relative_to(ROOT)) not in kept
    ]
    entries = [
        {"path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in files
    ]
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.apply else "dry_run",
        "file_count": len(entries),
        "total_bytes": sum(item["bytes"] for item in entries),
        "files": entries,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if args.apply:
        for path in files:
            path.unlink()
        for directory in sorted((path for path in RAW.rglob("*") if path.is_dir()), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass
    print(json.dumps({key: manifest[key] for key in ("mode", "file_count", "total_bytes")}, indent=2))


if __name__ == "__main__":
    main()
