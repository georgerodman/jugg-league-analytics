#!/usr/bin/env python3
"""Compare FantasyPros and FFA preseason projections with actual STD points."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def ffa_standard_points(stats: dict[str, Any], position: str) -> float | None:
    """Approximate FantasyPros standard scoring from FFA offensive stats."""
    if position not in {"QB", "RB", "WR", "TE"}:
        return None
    get = lambda key: float(stats.get(key) or 0)
    return (
        get("pass_yds") / 25 + get("pass_tds") * 4 - get("pass_ints") * 2
        + get("rush_yds") / 10 + get("rush_tds") * 6
        + get("rec_yds") / 10 + get("rec_tds") * 6
        + get("ret_tds") * 6 + get("2pt_tds") * 2 - get("fumbles_lost") * 2
    )


def metrics(rows: list[dict[str, Any]], prediction_key: str) -> dict[str, Any]:
    errors = [float(row[prediction_key]) - float(row["actual_points_std"]) for row in rows]
    if not errors:
        return {"n": 0, "mae": None, "rmse": None, "bias": None}
    return {
        "n": len(errors),
        "mae": round(statistics.fmean(abs(error) for error in errors), 3),
        "rmse": round(math.sqrt(statistics.fmean(error * error for error in errors)), 3),
        "bias": round(statistics.fmean(errors), 3),
    }


def load_pointer(root: Path, directory: str, season: int) -> dict[str, Any]:
    pointer = json.loads((root / "data" / "processed" / directory / str(season) / "latest.json").read_text())
    return json.loads((root / pointer["artifact"]).read_text())


def evaluate(root: Path, seasons: list[int]) -> Path:
    rows = []
    for season in seasons:
        canonical = load_pointer(root, "canonical_projections", season)
        actuals = load_pointer(root, "fantasypros_actuals", season)
        actual_by_id = {row["fantasypros_id"]: row for row in actuals["players"]}
        for player in canonical["players"]:
            if player["position"] not in {"QB", "RB", "WR", "TE"}:
                continue
            actual = actual_by_id.get(player["source_ids"]["fantasypros"])
            ffa = player.get("enrichments", {}).get("ffa")
            if not actual or actual.get("points_std") is None or not ffa:
                continue
            fp_prediction = player["fantasypros"].get("points_std")
            ffa_prediction = ffa_standard_points(ffa["stats"], player["position"])
            if fp_prediction is None or ffa_prediction is None:
                continue
            rows.append({
                "season": season, "fantasypros_id": player["source_ids"]["fantasypros"],
                "name": player["name"], "position": player["position"],
                "actual_points_std": actual["points_std"],
                "fantasypros_projected_points_std": fp_prediction,
                "ffa_projected_points_std": round(ffa_prediction, 3),
            })

    groups = {"all": rows}
    for season in seasons:
        groups[f"season:{season}"] = [row for row in rows if row["season"] == season]
    for position in ("QB", "RB", "WR", "TE"):
        groups[f"position:{position}"] = [row for row in rows if row["position"] == position]
    results = {}
    for name, group_rows in groups.items():
        results[name] = {
            "fantasypros": metrics(group_rows, "fantasypros_projected_points_std"),
            "ffa": metrics(group_rows, "ffa_projected_points_std"),
        }
    built_at = datetime.now(timezone.utc)
    build_id = built_at.strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "metadata": {
            "schema_version": 1, "build_id": build_id, "built_at": built_at.isoformat(),
            "seasons": seasons, "scoring": "FantasyPros STD approximation",
            "cohort": "Offensive players present in FantasyPros projections, FFA projections, and FantasyPros actual points",
            "limitations": [
                "FFA standard points are reconstructed with common STD rules because source-provided fantasy points are unavailable.",
                "This evaluates total-season fantasy points, not individual counting-stat accuracy.",
                "Players missing from either projection source are excluded for an equal-cohort comparison.",
            ],
            "row_count": len(rows),
        },
        "metrics": results, "rows": rows,
    }
    out_dir = root / "data" / "processed" / "projection_evaluation" / build_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "evaluation.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    latest = root / "data" / "processed" / "projection_evaluation" / "latest.json"
    latest.write_text(json.dumps({"schema_version": 1, "build_id": build_id, "artifact": str(path.relative_to(root))}, indent=2) + "\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=int, nargs="+", default=list(range(2020, 2026)))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(f"Wrote {evaluate(args.root.resolve(), args.seasons)}")
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"Evaluation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
