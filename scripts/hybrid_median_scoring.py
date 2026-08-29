#!/usr/bin/env python3
"""Recalculate Yahoo fantasy standings with a weekly median scoring point."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def calculate_season(payload: dict[str, Any]) -> dict[str, Any]:
    season = int(payload["season"])
    matchups = payload["matchups"]
    by_week: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for matchup in matchups:
        by_week[int(matchup["week"])].append(matchup)

    teams: dict[str, dict[str, Any]] = {}
    weekly: list[dict[str, Any]] = []

    for week in sorted(by_week):
        week_matchups = by_week[week]
        scores = [
            float(matchup[key])
            for matchup in week_matchups
            for key in ("score1", "score2")
        ]
        median = statistics.median(scores)

        for matchup in week_matchups:
            entries = (
                ("1", "2", "team1_id", "team1", "score1"),
                ("2", "1", "team2_id", "team2", "score2"),
            )
            for side, opponent_side, id_key, name_key, score_key in entries:
                team_id = str(matchup[id_key])
                opponent_id = str(matchup[f"team{opponent_side}_id"])
                score = float(matchup[score_key])
                opponent_score = float(matchup[f"score{opponent_side}"])
                h2h_point = 1.0 if score > opponent_score else 0.5 if score == opponent_score else 0.0
                median_point = 1.0 if score > median else 0.0
                row = teams.setdefault(
                    team_id,
                    {
                        "team_id": team_id,
                        "team": matchup[name_key],
                        "h2h_points": 0.0,
                        "median_points": 0.0,
                        "hybrid_points": 0.0,
                        "points_for": 0.0,
                        "games": 0,
                    },
                )
                row["team"] = matchup[name_key]
                row["h2h_points"] += h2h_point
                row["median_points"] += median_point
                row["hybrid_points"] += h2h_point + median_point
                row["points_for"] += score
                row["games"] += 1
                weekly.append(
                    {
                        "season": season,
                        "week": week,
                        "team_id": team_id,
                        "team": matchup[name_key],
                        "opponent_id": opponent_id,
                        "score": score,
                        "opponent_score": opponent_score,
                        "weekly_median": median,
                        "h2h_point": h2h_point,
                        "median_point": median_point,
                        "hybrid_points": h2h_point + median_point,
                    }
                )

    actual = sorted(teams.values(), key=lambda row: (-row["h2h_points"], -row["points_for"], row["team"]))
    hybrid = sorted(teams.values(), key=lambda row: (-row["hybrid_points"], -row["points_for"], row["team"]))
    actual_rank = {row["team_id"]: rank for rank, row in enumerate(actual, 1)}
    hybrid_rank = {row["team_id"]: rank for rank, row in enumerate(hybrid, 1)}

    standings = []
    for row in hybrid:
        result = dict(row)
        result["points_for"] = round(result["points_for"], 2)
        result["actual_rank"] = actual_rank[result["team_id"]]
        result["hybrid_rank"] = hybrid_rank[result["team_id"]]
        result["rank_change"] = result["actual_rank"] - result["hybrid_rank"]
        standings.append(result)

    return {
        "season": season,
        "weeks": len(by_week),
        "scoring": {
            "head_to_head_win": 1,
            "head_to_head_tie": 0.5,
            "strictly_above_weekly_median": 1,
            "at_or_below_weekly_median": 0,
            "standings_tiebreaker": "points_for",
        },
        "standings": standings,
        "weekly_results": weekly,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("data/raw/yahoo_weekly_scores"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/hybrid_median_scoring"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    seasons = []
    for path in sorted(args.input_dir.glob("[0-9][0-9][0-9][0-9].json")):
        payload = json.loads(path.read_text())
        expected = int(payload["regular_season_weeks"]) * 5
        if payload.get("errors") or len(payload["matchups"]) != expected:
            raise ValueError(f"{path}: expected {expected} validated matchups")
        result = calculate_season(payload)
        seasons.append(result)
        (args.output_dir / f"{result['season']}.json").write_text(json.dumps(result, indent=2) + "\n")

    summary_path = args.output_dir / "standings.csv"
    fields = ["season", "hybrid_rank", "actual_rank", "rank_change", "team_id", "team", "games", "h2h_points", "median_points", "hybrid_points", "points_for"]
    with summary_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for season in seasons:
            for row in season["standings"]:
                writer.writerow({"season": season["season"], **{field: row[field] for field in fields[1:]}})

    (args.output_dir / "summary.json").write_text(json.dumps(seasons, indent=2) + "\n")


if __name__ == "__main__":
    main()
