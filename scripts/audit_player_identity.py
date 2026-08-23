#!/usr/bin/env python3
"""Audit the latest identity registry against a versioned corroborated fixture."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path


def audit(root: Path) -> dict:
    latest = json.loads((root / "data" / "processed" / "nflverse" / "latest.json").read_text())
    registry_path = (root / latest["manifest"]).parent / "player_identity_crosswalk.json"
    registry = json.loads(registry_path.read_text())
    actual = {(int(row["season"]), int(row["fantasypros_id"])): row for row in registry["players"]}
    with (root / "tests" / "fixtures" / "player_identity_audit.csv").open(newline="", encoding="utf-8") as handle:
        expected = list(csv.DictReader(handle))
    failures = []
    for row in expected:
        key = (int(row["season"]), int(row["fantasypros_id"]))
        observed = actual.get(key)
        if not observed:
            failures.append({"key": key, "reason": "missing"})
            continue
        for field, expected_field in (("gsis_id", "expected_gsis_id"), ("yahoo_id", "expected_yahoo_id")):
            if observed.get(field) != row[expected_field]:
                failures.append({"key": key, "field": field, "expected": row[expected_field],
                                 "observed": observed.get(field)})
    return {"fixture_records": len(expected), "correct": len(expected) - len({tuple(x["key"]) for x in failures}),
            "precision": (len(expected) - len({tuple(x["key"]) for x in failures})) / len(expected),
            "failures": failures, "registry_collision_count": registry["metadata"].get("collision_count")}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    result = audit(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["failures"] or result["registry_collision_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
