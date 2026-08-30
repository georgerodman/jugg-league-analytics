#!/usr/bin/env python3
"""Build JUGG production values, a target-season decision board, and historical backtests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOCATION = {"QB": 15, "RB": 45, "WR": 48, "TE": 12, "K": 10, "DEF": 10}
ALLOCATION_VARIANTS = {
    "base": ALLOCATION,
    "2025_observed": {"QB": 15, "RB": 44, "WR": 48, "TE": 13, "K": 10, "DEF": 10},
    "rb_heavy_2021": {"QB": 15, "RB": 48, "WR": 46, "TE": 11, "K": 10, "DEF": 10},
    "qb_heavy_2020": {"QB": 17, "RB": 44, "WR": 48, "TE": 11, "K": 10, "DEF": 10},
}
STAT_KEYS = {
    "QB": ("passing_completions", "passing_attempts", "passing_yards", "passing_tds", "passing_interceptions", "rushing_attempts", "rushing_yards", "rushing_tds", "fumbles_lost"),
    "RB": ("rushing_attempts", "rushing_yards", "rushing_tds", "targets", "receptions", "receiving_yards", "receiving_tds", "fumbles_lost"),
    "WR": ("rushing_attempts", "rushing_yards", "rushing_tds", "targets", "receptions", "receiving_yards", "receiving_tds", "fumbles_lost"),
    "TE": ("targets", "receptions", "receiving_yards", "receiving_tds", "rushing_yards", "rushing_tds", "fumbles_lost"),
    "K": ("field_goals_made", "field_goals_attempted", "extra_points_made"),
    "DEF": ("sacks", "interceptions", "fumble_recoveries", "defensive_tds", "safeties", "special_teams_tds"),
}
PROJECTED_STAT_ALIASES = {
    "pass_cmp": "passing_completions", "pass_att": "passing_attempts", "pass_yds": "passing_yards",
    "pass_tds": "passing_tds", "pass_ints": "passing_interceptions", "rush_att": "rushing_attempts",
    "rush_yds": "rushing_yards", "rush_tds": "rushing_tds", "rec_rec": "receptions",
    "rec_yds": "receiving_yards", "rec_tds": "receiving_tds", "fumbles_lost": "fumbles_lost", "fg": "field_goals_made",
    "fga": "field_goals_attempted", "xpt": "extra_points_made", "def_sack": "sacks",
    "def_int": "interceptions", "def_fr": "fumble_recoveries", "def_td": "defensive_tds",
    "def_safety": "safeties", "def_retd": "special_teams_tds",
}
ACTUAL_STAT_ALIASES = {
    "completions": "passing_completions", "attempts": "passing_attempts", "passing_yards": "passing_yards",
    "passing_tds": "passing_tds", "passing_interceptions": "passing_interceptions", "carries": "rushing_attempts",
    "rushing_yards": "rushing_yards", "rushing_tds": "rushing_tds", "targets": "targets", "receptions": "receptions",
    "receiving_yards": "receiving_yards", "receiving_tds": "receiving_tds", "fg_made": "field_goals_made",
    "fumbles_lost_total": "fumbles_lost", "fg_att": "field_goals_attempted", "pat_made": "extra_points_made", "def_sacks": "sacks",
    "def_interceptions": "interceptions", "fumble_recovery_opp": "fumble_recoveries", "def_tds": "defensive_tds",
    "def_safeties": "safeties", "special_teams_tds": "special_teams_tds",
}


class ValueErrorModel(RuntimeError):
    pass


def training_seasons(target_season: int) -> tuple[int, ...]:
    seasons = tuple(range(2020, target_season))
    if len(seasons) < 2:
        raise ValueErrorModel("Target season must be 2022 or later")
    return seasons


def load_pointer(root: Path, path: str, key: str = "artifact") -> tuple[dict[str, Any], Path]:
    pointer = json.loads((root / path).read_text())
    artifact = root / pointer[key]
    return json.loads(artifact.read_text()), artifact


def production_values(players: list[dict[str, Any]], points_key: str, allocation: dict[str, int] = ALLOCATION) -> list[dict[str, Any]]:
    valued = []
    for position, slots in allocation.items():
        candidates = [row for row in players if row["position"] == position and row.get(points_key) is not None]
        candidates.sort(key=lambda row: (-float(row[points_key]), row.get("player_name") or row.get("name") or ""))
        if len(candidates) < slots:
            raise ValueErrorModel(f"Only {len(candidates)} {position} rows for {slots} slots")
        replacement = float(candidates[slots - 1][points_key])
        for rank, row in enumerate(candidates, 1):
            above = max(0.0, float(row[points_key]) - replacement)
            valued.append({**row, "position_rank": rank, "replacement_points": replacement,
                           "points_above_replacement": above, "modeled_roster_slot": rank <= slots})
    rostered = [row for row in valued if row["modeled_roster_slot"]]
    total_above = sum(row["points_above_replacement"] for row in rostered)
    dollars_per_point = 1860.0 / total_above
    for row in valued:
        row["production_value"] = round(1.0 + row["points_above_replacement"] * dollars_per_point, 2) if row["modeled_roster_slot"] else 0.0
    return valued


def assign_position_tiers(rows: list[dict[str, Any]], value_key: str, prefix: str,
                          maximum_span: float, minimum_natural_gap: float) -> None:
    """Assign deterministic, position-local tiers from natural gaps and bounded spans."""
    for position in ALLOCATION:
        ordered = sorted((row for row in rows if row["position"] == position and row.get(value_key) is not None),
                         key=lambda row: (-float(row[value_key]), row["player_name"]))
        if not ordered:
            continue
        gaps = [max(0.0, float(left[value_key])-float(right[value_key])) for left, right in zip(ordered, ordered[1:])]
        positive_gaps = [gap for gap in gaps if gap > 0]
        typical_gap = statistics.median(positive_gaps) if positive_gaps else 0.0
        natural_break = max(minimum_natural_gap, typical_gap * 2.5)
        tier = 1; tier_leader = float(ordered[0][value_key])
        for index, row in enumerate(ordered):
            if index:
                prior = float(ordered[index-1][value_key]); current = float(row[value_key])
                if prior-current >= natural_break or tier_leader-current > maximum_span:
                    tier += 1; tier_leader = current
            row[f"{prefix}_tier"] = tier
        for tier_number in range(1, tier+1):
            members = [row for row in ordered if row[f"{prefix}_tier"] == tier_number]
            high=max(float(row[value_key]) for row in members);low=min(float(row[value_key]) for row in members)
            for row in members:
                row[f"{prefix}_tier_size"] = len(members)
                row[f"{prefix}_tier_high"] = round(high, 2)
                row[f"{prefix}_tier_low"] = round(low, 2)


def number(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def normalized_projected_stat_lines(root: Path, season: int) -> tuple[dict[str, dict[str, Any]], Path]:
    payload, path = load_pointer(root, f"data/processed/canonical_projections/{season}/latest.json")
    lines = {}
    for player in payload["players"]:
        position=player["position"]; normalized={}
        for source_key, target_key in PROJECTED_STAT_ALIASES.items():
            if source_key in player.get("stats", {}) and target_key in STAT_KEYS[position]:
                normalized[target_key]=round(number(player["stats"][source_key]), 2)
        lines[player["internal_player_id"]]={"season":season,"games":None,"fantasy_points":round(number(player.get("fantasypros",{}).get("league_projected_points")),2),"stats":normalized,"source":"FantasyPros consensus projection"}
    return lines, path


def normalized_actual_stat_lines(root: Path, season: int, nfl_pointer: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], list[Path]]:
    directory=(root/nfl_pointer["manifest"]).parent
    actual_path=directory/"league_scored_actuals.json"; actual=json.loads(actual_path.read_text())
    summaries={row["internal_player_id"]:row for row in actual["seasons"] if row["season"]==season}
    aggregates:dict[str,dict[str,float]]={}
    player_path=directory/f"player_stats_{season}.csv"
    with player_path.open(newline="",encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            player_id=f"nfl:gsis:{row['player_id']}"; values=aggregates.setdefault(player_id,{})
            position=row["position"]
            if position not in STAT_KEYS: continue
            for source_key,target_key in ACTUAL_STAT_ALIASES.items():
                if source_key in row and target_key in STAT_KEYS[position]: values[target_key]=values.get(target_key,0)+number(row[source_key])
    team_path=directory/f"team_stats_{season}.csv"
    with team_path.open(newline="",encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            player_id=f"nfl:def:{row['team']}";values=aggregates.setdefault(player_id,{})
            for source_key,target_key in ACTUAL_STAT_ALIASES.items():
                if source_key in row and target_key in STAT_KEYS["DEF"]: values[target_key]=values.get(target_key,0)+number(row[source_key])
    lines={}
    for player_id,summary in summaries.items():
        if player_id not in aggregates: continue
        lines[player_id]={"season":season,"games":int(summary["games"]),"fantasy_points":round(number(summary["league_points"]),2),"points_per_game":round(number(summary["points_per_game"]),2),"stats":{key:round(value,2) for key,value in aggregates[player_id].items()},"source":"nflverse weekly player and team statistics"}
    return lines,[actual_path,player_path,team_path]


def player_biographies(root: Path, nfl_pointer: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], Path]:
    path=(root/nfl_pointer["manifest"]).parent/"players.csv"
    with path.open(newline="",encoding="utf-8") as handle: rows=list(csv.DictReader(handle))
    biographies={}
    for row in rows:
        if not row.get("gsis_id"): continue
        experience=row.get("years_of_experience")
        biographies[f"nfl:gsis:{row['gsis_id']}"]={"birth_date":row.get("birth_date") or None,"years_of_experience":int(float(experience)) if experience else None}
    return biographies,path


def projected_players(root: Path, season: int) -> tuple[list[dict[str, Any]], Path]:
    payload, path = load_pointer(root, f"data/processed/canonical_projections/{season}/latest.json")
    rows = []
    for player in payload["players"]:
        points = player.get("fantasypros", {}).get("league_projected_points")
        if points is not None:
            rows.append({"season": season, "internal_player_id": player["internal_player_id"],
                         "player_name": player["name"], "position": player["position"],
                         "nfl_team": player.get("nfl_team"), "projected_points": float(points)})
    return rows, path


def correlation(pairs: list[tuple[float, float]]) -> float | None:
    if len(pairs) < 2:
        return None
    xs, ys = zip(*pairs); xm, ym = statistics.fmean(xs), statistics.fmean(ys)
    denominator = math.sqrt(sum((x-xm)**2 for x in xs) * sum((y-ym)**2 for y in ys))
    return round(sum((x-xm)*(y-ym) for x,y in pairs) / denominator, 4) if denominator else None


def run(root: Path, season: int = 2026) -> Path:
    seasons = training_seasons(season)
    auction, auction_path = load_pointer(root, "data/processed/auction_history_matches/latest.json")
    nfl_pointer = json.loads((root / "data/processed/nflverse/latest.json").read_text())
    actual_path = (root / nfl_pointer["manifest"]).parent / "league_scored_actuals.json"
    actual_payload = json.loads(actual_path.read_text())
    actual_by_season = {}
    for historical_season in seasons:
        actual_rows = [{"season": historical_season, "internal_player_id": row["internal_player_id"],
                        "player_name": row["name"], "position": row["position"],
                        "actual_points": row["league_points"]}
                       for row in actual_payload["seasons"] if row["season"] == historical_season and row["position"] in ALLOCATION]
        actual_by_season[historical_season] = {row["internal_player_id"]: row for row in production_values(actual_rows, "actual_points")}
    backtest_rows = []
    inputs = {str(auction_path.relative_to(root)): hashlib.sha256(auction_path.read_bytes()).hexdigest(),
              str(actual_path.relative_to(root)): hashlib.sha256(actual_path.read_bytes()).hexdigest()}
    for historical_season in seasons:
        projections, projection_path = projected_players(root, historical_season)
        inputs[str(projection_path.relative_to(root))] = hashlib.sha256(projection_path.read_bytes()).hexdigest()
        projected = {row["internal_player_id"]: row for row in production_values(projections, "projected_points")}
        for sale in (row for row in auction["sales"] if row["season"] == historical_season):
            p, a = projected.get(sale["internal_player_id"]), actual_by_season[historical_season].get(sale["internal_player_id"])
            if not p or not a:
                continue
            backtest_rows.append({"season": historical_season, "internal_player_id": sale["internal_player_id"],
                "player_name": sale["player_name"], "position": sale["position"], "salary": sale["salary"],
                "projected_production_value": p["production_value"], "actual_production_value": a["production_value"],
                "predicted_surplus_at_sale": round(p["production_value"]-sale["salary"],2),
                "realized_surplus": round(a["production_value"]-sale["salary"],2)})
    pairs = [(r["predicted_surplus_at_sale"], r["realized_surplus"]) for r in backtest_rows]
    ordered = sorted(backtest_rows, key=lambda r:r["predicted_surplus_at_sale"], reverse=True)
    quartile = max(1, len(ordered)//4); top, rest = ordered[:quartile], ordered[quartile:]
    backtest = {"matched_sales":len(backtest_rows), "surplus_correlation":correlation(pairs),
        "top_quartile_mean_realized_surplus":round(statistics.fmean(r["realized_surplus"] for r in top),3),
        "remaining_mean_realized_surplus":round(statistics.fmean(r["realized_surplus"] for r in rest),3),
        "top_quartile_positive_realized_rate":round(statistics.fmean(r["realized_surplus"]>0 for r in top),4)}
    backtest["by_position"] = {}
    for position in ALLOCATION:
        position_rows = [row for row in backtest_rows if row["position"] == position]
        position_ordered = sorted(position_rows, key=lambda row: row["predicted_surplus_at_sale"], reverse=True)
        cut = max(1, len(position_ordered)//4)
        backtest["by_position"][position] = {
            "n": len(position_rows),
            "surplus_correlation": correlation([(row["predicted_surplus_at_sale"], row["realized_surplus"]) for row in position_rows]),
            "top_quartile_mean_realized_surplus": round(statistics.fmean(row["realized_surplus"] for row in position_ordered[:cut]),3),
            "remaining_mean_realized_surplus": round(statistics.fmean(row["realized_surplus"] for row in position_ordered[cut:]),3),
        }

    target_projections, projection_path = projected_players(root, season)
    inputs[str(projection_path.relative_to(root))] = hashlib.sha256(projection_path.read_bytes()).hexdigest()
    projected_stat_lines, projected_stat_path = normalized_projected_stat_lines(root, season)
    historical_stat_lines={};actual_stat_paths=[]
    actual_seasons = (season - 2, season - 1)
    for actual_season in actual_seasons:
        season_lines,season_paths=normalized_actual_stat_lines(root,actual_season,nfl_pointer)
        historical_stat_lines[actual_season]=season_lines;actual_stat_paths.extend(season_paths)
    actual_stat_lines=historical_stat_lines[season - 1]
    biographies, biographies_path = player_biographies(root, nfl_pointer)
    inputs[str(projected_stat_path.relative_to(root))] = hashlib.sha256(projected_stat_path.read_bytes()).hexdigest()
    for stat_path in actual_stat_paths:
        inputs[str(stat_path.relative_to(root))] = hashlib.sha256(stat_path.read_bytes()).hexdigest()
    inputs[str(biographies_path.relative_to(root))] = hashlib.sha256(biographies_path.read_bytes()).hexdigest()
    target_values = {row["internal_player_id"]: row for row in production_values(target_projections,"projected_points")}
    variant_values = {
        name: {row["internal_player_id"]: row for row in production_values(target_projections, "projected_points", allocation)}
        for name, allocation in ALLOCATION_VARIANTS.items()
    }
    price_pointer = json.loads((root / "data/processed/auction_price_model/latest.json").read_text())
    price_path = root / price_pointer[f"scores_{season}_json"]; prices = json.loads(price_path.read_text())
    inputs[str(price_path.relative_to(root))] = hashlib.sha256(price_path.read_bytes()).hexdigest()
    board=[]
    for market in prices["players"]:
        value=target_values.get(market["internal_player_id"])
        if not value: continue
        variants = [rows[market["internal_player_id"]]["production_value"] for rows in variant_values.values()]
        flags = []
        missing_inputs = market.get("missing_inputs", [])
        core_missing = [name for name in ("espn_salary_cap_value", "adp_espn", "adp_yahoo") if market.get(name) is None]
        if len(core_missing) >= 2: flags.append("missing_market_inputs")
        if market["position"] in {"K", "DEF"}: flags.append("low_confidence_special_teams_projection")
        if market["price_range_high"] - market["price_range_low"] >= 10: flags.append("wide_market_price_range")
        if market["draft_probability"] < 0.4: flags.append("low_draft_probability")
        if abs(value["position_rank"] - ALLOCATION[value["position"]]) <= 3: flags.append("replacement_boundary")
        if max(variants)-min(variants) >= 3: flags.append("allocation_sensitive")
        biography=biographies.get(market["internal_player_id"],{})
        board.append({"internal_player_id":market["internal_player_id"],"player_name":market["player_name"],
            "position":market["position"],"nfl_team":market.get("nfl_team"),
            "birth_date":biography.get("birth_date"),"years_of_experience":biography.get("years_of_experience"),
            "draft_probability":market["draft_probability"],"expected_jugg_price":market["expected_jugg_price_if_drafted"],
            "price_range_low":market["price_range_low"],"price_range_high":market["price_range_high"],
            "projected_points":value["projected_points"],"position_rank":value["position_rank"],
            "replacement_points":value["replacement_points"],"points_above_replacement":round(value["points_above_replacement"],2),
            "production_value":value["production_value"],
            "expected_surplus":round(value["production_value"]-market["expected_jugg_price_if_drafted"],2),
            "production_value_low":min(variants),"production_value_high":max(variants),
            "allocation_value_spread":round(max(variants)-min(variants),2),
            "espn_salary_cap_value":market.get("espn_salary_cap_value"),
            "adp_espn":market.get("adp_espn"),"adp_yahoo":market.get("adp_yahoo"),
            "market_missing_inputs":";".join(core_missing),"prior_price_missing":"prior_jugg_salary" in missing_inputs,
            "risk_flags":";".join(flags),
            "modeled_roster_slot":value["modeled_roster_slot"],
            "last_season_stat_line":actual_stat_lines.get(market["internal_player_id"]),
            "historical_stat_lines":[historical_stat_lines[actual_season][market["internal_player_id"]] for actual_season in actual_seasons if market["internal_player_id"] in historical_stat_lines[actual_season]],
            "projected_stat_line":projected_stat_lines.get(market["internal_player_id"])})
    assign_position_tiers(board,"projected_points","production",maximum_span=16.0,minimum_natural_gap=6.0)
    assign_position_tiers(board,"expected_jugg_price","auction",maximum_span=5.0,minimum_natural_gap=2.0)
    board.sort(key=lambda r:(-r["expected_surplus"],-r["draft_probability"],r["player_name"]))
    for rank,row in enumerate(board,1): row["surplus_rank"]=rank
    built=datetime.now(timezone.utc); build_id=built.strftime("%Y%m%dT%H%M%SZ")
    out=root/"data/processed/production_value_model"/build_id; out.mkdir(parents=True,exist_ok=True)
    fields=list(board[0]);
    board_csv = out/f"decision_board_{season}.csv"
    board_json = out/f"decision_board_{season}.json"
    with board_csv.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(board)
    hardening = {"allocation_variants": ALLOCATION_VARIANTS,
        "allocation_sensitive_count":sum("allocation_sensitive" in row["risk_flags"] for row in board),
        "risk_flag_counts":{flag:sum(flag in row["risk_flags"].split(";") for row in board) for flag in ["missing_market_inputs","low_confidence_special_teams_projection","wide_market_price_range","low_draft_probability","replacement_boundary","allocation_sensitive"]},
        "top_20_bargain_positions":{position:sum(row["position"]==position for row in board[:20]) for position in ALLOCATION}}
    tier_contract={"scope":"position","production":{"value":"projected_points","maximum_within_tier_span":16.0,"minimum_natural_gap":6.0,"natural_gap_multiplier":2.5},"auction":{"value":"expected_jugg_price","maximum_within_tier_span":5.0,"minimum_natural_gap":2.0,"natural_gap_multiplier":2.5}}
    board_json.write_text(json.dumps({"metadata":{"schema_version":2,"build_id":build_id,"season":season,"allocation":ALLOCATION,"tier_contract":tier_contract,"stat_line_contract":{"actual_seasons":list(actual_seasons),"projection_season":season},"inputs":inputs,"hardening":hardening},"players":board},indent=2,sort_keys=True)+"\n")
    (out/"backtest.json").write_text(json.dumps({"metadata":{"schema_version":1,"build_id":build_id},"summary":backtest,"rows":backtest_rows},indent=2,sort_keys=True)+"\n")
    latest=root/"data/processed/production_value_model/latest.json"
    latest.write_text(json.dumps({"schema_version":1,"build_id":build_id,"season":season,"decision_board_json":str(board_json.relative_to(root)),"decision_board_csv":str(board_csv.relative_to(root)),"backtest":str((out/"backtest.json").relative_to(root))},indent=2)+"\n")
    return out


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--season",type=int,default=2026,help="Season to score; prior seasons become training data")
    args=parser.parse_args()
    try: print(f"Wrote {run(args.root.resolve(),args.season)}")
    except (OSError,KeyError,ValueError,json.JSONDecodeError,ValueErrorModel) as exc:
        print(f"Production value model failed: {exc}",file=sys.stderr);raise SystemExit(1)
