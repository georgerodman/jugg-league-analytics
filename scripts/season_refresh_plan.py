#!/usr/bin/env python3
"""Create a non-mutating, ordered import and model-refresh plan for a future season."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def step(
    name: str,
    phase: str,
    status: str,
    detail: str,
    command: list[str] | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {"name": name, "phase": phase, "status": status, "detail": detail}
    if command:
        item["command"] = command
    return item


def build_plan(root: Path, season: int) -> dict[str, Any]:
    active_path = root / "config" / "active-season.json"
    active = json.loads(active_path.read_text(encoding="utf-8"))
    prior_season = season - 1
    future = season > active["season"]

    steps = [
        step(
            "validate_target_season",
            "safety",
            "ready" if future else "blocked",
            f"Target {season} is later than active season {active['season']}." if future else f"Target {season} must be later than active season {active['season']}.",
        ),
        step(
            "preserve_historical_model_inputs",
            "prerequisite",
            "manual",
            "Keep the external model-data archive available. Restore it only if a model rebuild needs a pruned historical input; do not copy it into the repository preemptively.",
        ),
        step(
            "fantasypros_projections",
            "acquire",
            "available",
            f"Download and normalize {season} projections.",
            ["python3", "scripts/fantasypros_projections.py", "--season", str(season)],
        ),
        step(
            "fantasypros_adp",
            "acquire",
            "available",
            f"Download and normalize {season} ADP.",
            ["python3", "scripts/fantasypros_adp.py", "--seasons", str(season)],
        ),
        step(
            "fantasypros_context",
            "acquire",
            "available",
            f"Download injuries and news for {season}.",
            ["python3", "scripts/fantasypros_context.py", "--season", str(season)],
        ),
        step(
            "nflverse_history",
            "acquire",
            "available",
            f"Refresh historical results through {prior_season}, including {season} identities.",
            ["python3", "scripts/nflverse_pipeline.py", "--seasons", *[str(year) for year in range(2020, season)], "--identity-seasons", str(season)],
        ),
        step(
            "nflverse_depth_charts",
            "acquire",
            "available",
            f"Download and normalize {season} depth charts.",
            ["python3", "scripts/nflverse_depth_charts.py", "--season", str(season)],
        ),
        step(
            "espn_salary_cap_values",
            "acquire",
            "manual",
            f"Place the {season} ESPN salary-cap PDF in the documented raw-data folder, then run the parser.",
            ["python3", "scripts/espn_salary_cap_values.py"],
        ),
        step(
            "canonical_projections",
            "prepare",
            "available",
            f"Build canonical projection snapshots through {season}.",
            ["python3", "scripts/build_canonical_projections.py", "--seasons", *[str(year) for year in range(2020, season + 1)]],
        ),
        step(
            "auction_price_model",
            "model",
            "available",
            f"Train on completed seasons and score the {season} player pool.",
            ["python3", "scripts/auction_price_model.py", "--season", str(season)],
        ),
        step(
            "production_value_model",
            "model",
            "available",
            f"Build production values and the {season} decision board.",
            ["python3", "scripts/production_value_model.py", "--season", str(season)],
        ),
        step(
            "rollover_readiness",
            "verify",
            "available",
            "Run the independent readiness gate after all target artifacts exist.",
            ["python3", "scripts/season_rollover_readiness.py", "--season", str(season)],
        ),
    ]
    blockers = [item for item in steps if item["status"] in {"blocked", "code_change_required"}]
    manual = [item for item in steps if item["status"] == "manual"]
    return {
        "schemaVersion": 1,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "mode": "dry_run",
        "activeSeason": active["season"],
        "targetSeason": season,
        "executableNow": not blockers and not manual,
        "summary": {
            "available": sum(item["status"] == "available" for item in steps),
            "manual": len(manual),
            "blockers": len(blockers),
        },
        "steps": steps,
        "safety": "No downloads ran; no artifact pointer, database, active-season configuration, or Google Sheet was changed.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    plan = build_plan(ROOT, args.season)
    output = args.output or ROOT / ".local" / "readiness" / f"refresh-{args.season}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "executableNow": plan["executableNow"], **plan["summary"], "safety": plan["safety"]}, indent=2))


if __name__ == "__main__":
    main()
