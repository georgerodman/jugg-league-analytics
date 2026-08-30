#!/usr/bin/env python3
"""Create a checksummed archive of season data before postseason pruning."""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def included_files() -> list[Path]:
    roots = [ROOT / "data", ROOT / "config"]
    files = [
        path
        for source in roots
        for path in source.rglob("*")
        if path.is_file() and path.name != ".DS_Store" and "__pycache__" not in path.parts
    ]
    files.extend(path for path in [ROOT / "requirements-data.txt"] if path.is_file())
    return sorted(set(files), key=lambda path: str(path.relative_to(ROOT)))


def create_archive(season: int, destination: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    archive = destination / f"jugg-{season}-model-data-{timestamp}.tar.gz"
    files = included_files()
    manifest = {
        "schema_version": 1,
        "season": season,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Preserve source and derived model data before postseason repository pruning.",
        "git_tag": f"draft-{season}-final",
        "file_count": len(files),
        "total_bytes": sum(path.stat().st_size for path in files),
        "files": [
            {
                "path": str(path.relative_to(ROOT)),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in files
        ],
    }
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        manifest_path = Path(temporary) / "MANIFEST.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(manifest_path, arcname="MANIFEST.json")
            for path in files:
                bundle.add(path, arcname=str(path.relative_to(ROOT)), recursive=False)
    print(
        json.dumps(
            {
                "archive": str(archive),
                "bytes": archive.stat().st_size,
                "sha256": sha256(archive),
                "files": len(files),
            },
            indent=2,
        )
    )
    return archive


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument(
        "--destination",
        type=Path,
        default=ROOT / ".local" / "archives",
        help="Destination directory outside version control.",
    )
    args = parser.parse_args()
    create_archive(args.season, args.destination.resolve())


if __name__ == "__main__":
    main()
