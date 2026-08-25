#!/usr/bin/env python3
"""Safely rebuild all derived JUGG model artifacts from current local inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STAGES = (
    ("canonical_projections", "build_canonical_projections.py"),
    ("projection_match_report", "projection_match_report.py"),
    ("auction_history_matches", "match_auction_history.py"),
    ("projection_evaluation", "evaluate_projection_sources.py"),
    ("auction_price_and_probability", "auction_price_model.py"),
    ("production_value_and_decision_board", "production_value_model.py"),
    ("owner_tendencies", "owner_tendencies.py"),
    ("championship_equity_standalone", "championship_equity.py"),
    ("championship_decisions_standalone", "championship_decisions.py"),
)


class RebuildError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pointers(root: Path) -> dict[Path, bytes]:
    return {path: path.read_bytes() for path in (root / "data" / "processed").glob("**/latest.json")}


def restore_pointers(root: Path, before: dict[Path, bytes]) -> None:
    current = set((root / "data" / "processed").glob("**/latest.json"))
    for path in current - set(before):
        path.unlink()
    for path, content in before.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".rollback.tmp")
        temporary.write_bytes(content)
        os.replace(temporary, path)


def load_board(root: Path, pointer_bytes: bytes | None) -> list[dict[str, Any]]:
    if not pointer_bytes:
        return []
    pointer = json.loads(pointer_bytes)
    artifact = pointer.get("decision_board_json")
    return json.loads((root / artifact).read_text())["players"] if artifact else []


def compare_boards(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> dict[str, Any]:
    old = {row["internal_player_id"]: row for row in before}
    new = {row["internal_player_id"]: row for row in after}
    changes = []
    for player_id in sorted(old.keys() & new.keys()):
        left, right = old[player_id], new[player_id]
        changes.append({
            "internal_player_id": player_id, "player_name": right["player_name"],
            "expected_price_change": round(right["expected_jugg_price"] - left["expected_jugg_price"], 2),
            "draft_probability_change": round(right["draft_probability"] - left["draft_probability"], 4),
            "production_value_change": round(right["production_value"] - left["production_value"], 2),
            "surplus_change": round(right["expected_surplus"] - left["expected_surplus"], 2),
        })
    material = [row for row in changes if any(row[key] != 0 for key in
                ("expected_price_change", "draft_probability_change", "production_value_change", "surplus_change"))]
    return {
        "previous_count": len(before), "new_count": len(after),
        "added_players": sorted(new.keys() - old.keys()), "removed_players": sorted(old.keys() - new.keys()),
        "changed_player_count": len(material),
        "largest_absolute_surplus_changes": sorted(material, key=lambda row: abs(row["surplus_change"]), reverse=True)[:25],
    }


def validate_inputs(root: Path) -> None:
    required = [root / "config/league.json", root / "data/raw/auction_history.csv",
                root / "data/processed/nflverse/latest.json"]
    required.extend(root / f"data/processed/fantasypros/{season}/latest.json" for season in range(2020, 2027))
    required.extend(root / f"data/processed/fantasypros_adp/{season}/latest.json" for season in range(2020, 2027))
    missing = [str(path.relative_to(root)) for path in required if not path.exists()]
    if missing:
        raise RebuildError(f"Missing required inputs: {missing}")
    league = json.loads((root / "config/league.json").read_text())
    if league["league"]["team_count"] != 10 or league["auction"]["budget_per_team"] != 200:
        raise RebuildError("Model assumptions require the validated 10-team, $200 JUGG configuration")


def run(root: Path) -> Path:
    validate_inputs(root)
    started = datetime.now(timezone.utc); build_id = started.strftime("%Y%m%dT%H%M%SZ")
    out = root / "data" / "processed" / "rebuilds" / build_id; out.mkdir(parents=True, exist_ok=True)
    before = pointers(root)
    production_pointer = root / "data/processed/production_value_model/latest.json"
    previous_board = load_board(root, before.get(production_pointer))
    stage_records = []
    try:
        for name, script in STAGES:
            result = subprocess.run([sys.executable, str(root / "scripts" / script)], cwd=root,
                                    capture_output=True, text=True)
            (out / f"{name}.log").write_text(result.stdout + result.stderr)
            stage_records.append({"name": name, "script": f"scripts/{script}", "exit_code": result.returncode})
            if result.returncode:
                raise RebuildError(f"Stage failed: {name}; see {out / f'{name}.log'}")
        tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
                               cwd=root, capture_output=True, text=True,
                               env={**os.environ, "PYTHONPYCACHEPREFIX": "/tmp/jugg-rebuild-pycache"})
        (out / "tests.log").write_text(tests.stdout + tests.stderr)
        stage_records.append({"name": "tests", "exit_code": tests.returncode})
        if tests.returncode:
            raise RebuildError(f"Tests failed; see {out / 'tests.log'}")
        domain_tests = subprocess.run(["npm", "run", "typecheck"], cwd=root, capture_output=True, text=True)
        if domain_tests.returncode == 0:
            executed = subprocess.run(["npm", "run", "test:domain"], cwd=root, capture_output=True, text=True)
            domain_tests = subprocess.CompletedProcess(domain_tests.args, executed.returncode,
                domain_tests.stdout + domain_tests.stderr + executed.stdout, executed.stderr)
        (out / "domain_tests.log").write_text(domain_tests.stdout + domain_tests.stderr)
        stage_records.append({"name": "domain_typecheck_and_tests", "exit_code": domain_tests.returncode})
        if domain_tests.returncode:
            raise RebuildError(f"Domain verification failed; see {out / 'domain_tests.log'}")
        current = pointers(root)
        new_board = load_board(root, current.get(production_pointer))
        if len(new_board) != 294:
            raise RebuildError(f"Decision board integrity failure: expected 294 rows, found {len(new_board)}")
        comparison = compare_boards(previous_board, new_board)
        (out / "board_comparison.json").write_text(json.dumps(comparison, indent=2, sort_keys=True) + "\n")
        manifest = {"schema_version": 1, "build_id": build_id, "started_at": started.isoformat(),
                    "completed_at": datetime.now(timezone.utc).isoformat(), "status": "complete",
                    "stages": stage_records,
                    "published_pointers": {str(path.relative_to(root)): sha256(path) for path in sorted(current)},
                    "comparison": "board_comparison.json"}
        manifest_path = out / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        latest = root / "data/processed/rebuilds/latest.json"
        latest.write_text(json.dumps({"schema_version": 1, "build_id": build_id,
                                      "manifest": str(manifest_path.relative_to(root))}, indent=2) + "\n")
        return manifest_path
    except Exception:
        restore_pointers(root, before)
        (out / "failure.json").write_text(json.dumps({"schema_version": 1, "build_id": build_id,
            "status": "failed", "failed_at": datetime.now(timezone.utc).isoformat(), "stages": stage_records}, indent=2) + "\n")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(f"Rebuild complete: {run(args.root.resolve())}")
    except (OSError, KeyError, ValueError, json.JSONDecodeError, RebuildError) as exc:
        print(f"Rebuild failed safely: {exc}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
