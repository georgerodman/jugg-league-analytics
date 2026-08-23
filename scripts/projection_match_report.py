#!/usr/bin/env python3
"""Create a combined CSV review queue from canonical match exceptions."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DRAFTABLE_REVIEW_BANDS = {"QB": 20, "RB": 50, "WR": 60, "TE": 20, "K": 15, "DEF": 15}


def run(root: Path, seasons: list[int]) -> Path:
    rows = []
    summary = {}
    for season in seasons:
        pointer = json.loads((root / "data" / "processed" / "canonical_projections" / str(season) / "latest.json").read_text())
        artifact = root / pointer["artifact"]
        canonical = json.loads(artifact.read_text())
        ranking = {}
        for position, cutoff in DRAFTABLE_REVIEW_BANDS.items():
            players = sorted(
                (player for player in canonical["players"] if player["position"] == position),
                key=lambda player: float(player["fantasypros"].get("points_std") or player["fantasypros"]["league_projected_points"] or 0),
                reverse=True,
            )
            for rank, player in enumerate(players, start=1):
                ranking[player["source_ids"]["fantasypros"]] = (rank, cutoff, float(player["fantasypros"].get("points_std") or player["fantasypros"]["league_projected_points"] or 0))
        exceptions = json.loads((artifact.parent / "match_exceptions.json").read_text())["exceptions"]
        counts = Counter(item["reason"] for item in exceptions)
        summary[str(season)] = dict(counts)
        for item in exceptions:
            rank, cutoff, points = ranking[item["fantasypros_id"]]
            significant = rank <= cutoff
            rows.append({
                "season": season, "reason": item["reason"], "fantasypros_id": item["fantasypros_id"],
                "name": item["name"], "position": item["position"], "team": item.get("team"),
                "ffa_candidates": " | ".join(item.get("ffa_candidates", [])),
                "projected_points": round(points, 3), "position_rank": rank,
                "review_band_cutoff": cutoff, "significant_projection": "yes" if significant else "no",
                "action_needed": "yes" if item["reason"] == "ambiguous_name_position" else "no",
                "recommended_action": "Review candidates and add a scoped alias" if item["reason"] == "ambiguous_name_position" else "None; FFA has no matching enrichment row",
            })
    built_at = datetime.now(timezone.utc)
    build_id = built_at.strftime("%Y%m%dT%H%M%SZ")
    out_dir = root / "data" / "processed" / "projection_match_review" / build_id
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "match_exceptions.csv"
    fields = ["season", "reason", "fantasypros_id", "name", "position", "team", "projected_points",
              "position_rank", "review_band_cutoff", "significant_projection", "ffa_candidates",
              "action_needed", "recommended_action"]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (out_dir / "summary.json").write_text(json.dumps({
        "schema_version": 1, "build_id": build_id, "built_at": built_at.isoformat(),
        "seasons": seasons, "exception_count": len(rows), "action_needed_count": sum(row["action_needed"] == "yes" for row in rows),
        "significant_projection_count": sum(row["significant_projection"] == "yes" for row in rows),
        "by_season": summary,
    }, indent=2, sort_keys=True) + "\n")
    latest = root / "data" / "processed" / "projection_match_review" / "latest.json"
    latest.write_text(json.dumps({"schema_version": 1, "build_id": build_id, "csv": str(csv_path.relative_to(root)), "summary": str((out_dir / 'summary.json').relative_to(root))}, indent=2) + "\n")
    return csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=int, nargs="+", default=list(range(2020, 2027)))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    print(f"Wrote {run(args.root.resolve(), args.seasons)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
