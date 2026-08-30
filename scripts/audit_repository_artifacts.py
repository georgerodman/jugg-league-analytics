#!/usr/bin/env python3
"""Inventory the current app/test artifact closure before repository pruning."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / ".local" / "audits" / "repository-artifacts.json"

RUNTIME_ROOTS = [
    "data/processed/production_value_model/latest.json",
    "data/processed/owner_tendencies/latest.json",
    "data/processed/espn_salary_cap_values/2026/latest.json",
    "data/processed/canonical_projections/2026/latest.json",
    "data/processed/fantasypros_adp/2026/latest.json",
    "data/processed/nflverse/latest.json",
    "data/processed/nflverse_depth_charts/2026/latest.json",
    "data/processed/fantasypros_context/2026/latest.json",
    "data/processed/fantasy_context/latest.json",
    "data/processed/fantasy_analysis/latest.json",
    "data/processed/fantasy_research/latest.json",
]

TEST_ROOTS = [
    "data/processed/draft_simulations/latest.json",
]


def published_roots() -> list[str]:
    return [str(path.relative_to(ROOT)) for path in sorted((ROOT / "data").rglob("latest.json"))]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def possible_paths(value: Any) -> list[str]:
    if isinstance(value, str) and value.startswith("data/"):
        return [value]
    if isinstance(value, list):
        return [path for item in value for path in possible_paths(item)]
    if isinstance(value, dict):
        return [path for item in value.values() for path in possible_paths(item)]
    return []


def closure(roots: list[str]) -> tuple[set[str], set[str]]:
    pending = list(roots)
    found: set[str] = set()
    missing: set[str] = set()
    while pending:
        relative = pending.pop()
        if relative in found or relative in missing:
            continue
        path = ROOT / relative
        if not path.is_file():
            missing.add(relative)
            continue
        found.add(relative)
        if path.suffix != ".json":
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        pending.extend(possible_paths(payload))
        if relative == "data/processed/nflverse/latest.json" and payload.get("snapshot_id"):
            pending.append(f"data/processed/nflverse/{payload['snapshot_id']}/player_stats_2025.csv")
    return found, missing


def published_closure(roots: list[str]) -> tuple[set[str], set[str]]:
    found, missing = closure(roots)
    build_pattern = re.compile(r"^(?:\d{8}T\d{6}Z|[0-9a-f]{16})$")
    while True:
        companions: set[str] = set()
        for relative in found:
            parent = (ROOT / relative).parent
            if build_pattern.fullmatch(parent.name):
                companions.update(str(path.relative_to(ROOT)) for path in parent.rglob("*") if path.is_file())
        new_roots = companions - found
        if not new_roots:
            return found, missing
        expanded, expanded_missing = closure(sorted(new_roots))
        found.update(expanded)
        missing.update(expanded_missing)


def describe(paths: set[str]) -> dict[str, Any]:
    files = []
    for relative in sorted(paths):
        path = ROOT / relative
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": digest(path)})
    return {"file_count": len(files), "total_bytes": sum(item["bytes"] for item in files), "files": files}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    runtime, runtime_missing = closure(RUNTIME_ROOTS)
    tests, test_missing = closure(TEST_ROOTS)
    published, published_missing = published_closure(published_roots())
    report = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "Conservative artifact closure used by the current application and checked-in tests.",
        "runtime": describe(runtime),
        "tests": describe(tests),
        "published": describe(published),
        "missing": {
            "runtime": sorted(runtime_missing),
            "tests": sorted(test_missing),
            "published": sorted(published_missing),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
