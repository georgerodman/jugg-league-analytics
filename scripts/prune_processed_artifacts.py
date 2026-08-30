#!/usr/bin/env python3
"""Remove superseded processed artifacts not reachable from a published pointer."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DEFAULT_AUDIT = ROOT / ".local" / "audits" / "repository-artifacts.json"
DEFAULT_MANIFEST = ROOT / ".local" / "audits" / "processed-prune-candidates.json"


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


def candidates(audit_path: Path) -> list[Path]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    missing = [path for paths in audit["missing"].values() for path in paths]
    if missing:
        raise RuntimeError(f"Artifact audit has missing dependencies: {', '.join(missing)}")
    kept = keep_paths(audit)
    return [
        path
        for path in sorted(PROCESSED.rglob("*"))
        if path.is_file() and str(path.relative_to(ROOT)) not in kept
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--apply", action="store_true", help="Delete the reviewed candidates")
    args = parser.parse_args()

    files = candidates(args.audit)
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
        for directory in sorted((path for path in PROCESSED.rglob("*") if path.is_dir()), reverse=True):
            try:
                directory.rmdir()
            except OSError:
                pass

    print(json.dumps({key: manifest[key] for key in ("mode", "file_count", "total_bytes")}, indent=2))


if __name__ == "__main__":
    main()
