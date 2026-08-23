#!/usr/bin/env python3
"""Build JUGG production values, a 2026 decision board, and historical backtests."""

from __future__ import annotations

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
SEASONS = tuple(range(2020, 2026))


class ValueErrorModel(RuntimeError):
    pass


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


def run(root: Path) -> Path:
    auction, auction_path = load_pointer(root, "data/processed/auction_history_matches/latest.json")
    nfl_pointer = json.loads((root / "data/processed/nflverse/latest.json").read_text())
    actual_path = (root / nfl_pointer["manifest"]).parent / "league_scored_actuals.json"
    actual_payload = json.loads(actual_path.read_text())
    actual_by_season = {}
    for season in SEASONS:
        actual_rows = [{"season": season, "internal_player_id": row["internal_player_id"],
                        "player_name": row["name"], "position": row["position"],
                        "actual_points": row["league_points"]}
                       for row in actual_payload["seasons"] if row["season"] == season and row["position"] in ALLOCATION]
        actual_by_season[season] = {row["internal_player_id"]: row for row in production_values(actual_rows, "actual_points")}
    backtest_rows = []
    inputs = {str(auction_path.relative_to(root)): hashlib.sha256(auction_path.read_bytes()).hexdigest(),
              str(actual_path.relative_to(root)): hashlib.sha256(actual_path.read_bytes()).hexdigest()}
    for season in SEASONS:
        projections, projection_path = projected_players(root, season)
        inputs[str(projection_path.relative_to(root))] = hashlib.sha256(projection_path.read_bytes()).hexdigest()
        projected = {row["internal_player_id"]: row for row in production_values(projections, "projected_points")}
        for sale in (row for row in auction["sales"] if row["season"] == season):
            p, a = projected.get(sale["internal_player_id"]), actual_by_season[season].get(sale["internal_player_id"])
            if not p or not a:
                continue
            backtest_rows.append({"season": season, "internal_player_id": sale["internal_player_id"],
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

    projections_2026, projection_path = projected_players(root, 2026)
    inputs[str(projection_path.relative_to(root))] = hashlib.sha256(projection_path.read_bytes()).hexdigest()
    values_2026 = {row["internal_player_id"]: row for row in production_values(projections_2026,"projected_points")}
    variant_values = {
        name: {row["internal_player_id"]: row for row in production_values(projections_2026, "projected_points", allocation)}
        for name, allocation in ALLOCATION_VARIANTS.items()
    }
    price_pointer = json.loads((root / "data/processed/auction_price_model/latest.json").read_text())
    price_path = root / price_pointer["scores_2026_json"]; prices = json.loads(price_path.read_text())
    inputs[str(price_path.relative_to(root))] = hashlib.sha256(price_path.read_bytes()).hexdigest()
    board=[]
    for market in prices["players"]:
        value=values_2026.get(market["internal_player_id"])
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
        board.append({"internal_player_id":market["internal_player_id"],"player_name":market["player_name"],
            "position":market["position"],"nfl_team":market.get("nfl_team"),
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
            "modeled_roster_slot":value["modeled_roster_slot"]})
    board.sort(key=lambda r:(-r["expected_surplus"],-r["draft_probability"],r["player_name"]))
    for rank,row in enumerate(board,1): row["surplus_rank"]=rank
    built=datetime.now(timezone.utc); build_id=built.strftime("%Y%m%dT%H%M%SZ")
    out=root/"data/processed/production_value_model"/build_id; out.mkdir(parents=True,exist_ok=True)
    fields=list(board[0]);
    with (out/"decision_board_2026.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(board)
    hardening = {"allocation_variants": ALLOCATION_VARIANTS,
        "allocation_sensitive_count":sum("allocation_sensitive" in row["risk_flags"] for row in board),
        "risk_flag_counts":{flag:sum(flag in row["risk_flags"].split(";") for row in board) for flag in ["missing_market_inputs","low_confidence_special_teams_projection","wide_market_price_range","low_draft_probability","replacement_boundary","allocation_sensitive"]},
        "top_20_bargain_positions":{position:sum(row["position"]==position for row in board[:20]) for position in ALLOCATION}}
    (out/"decision_board_2026.json").write_text(json.dumps({"metadata":{"schema_version":1,"build_id":build_id,"allocation":ALLOCATION,"inputs":inputs,"hardening":hardening},"players":board},indent=2,sort_keys=True)+"\n")
    (out/"backtest.json").write_text(json.dumps({"metadata":{"schema_version":1,"build_id":build_id},"summary":backtest,"rows":backtest_rows},indent=2,sort_keys=True)+"\n")
    latest=root/"data/processed/production_value_model/latest.json"
    latest.write_text(json.dumps({"schema_version":1,"build_id":build_id,"decision_board_json":str((out/"decision_board_2026.json").relative_to(root)),"decision_board_csv":str((out/"decision_board_2026.csv").relative_to(root)),"backtest":str((out/"backtest.json").relative_to(root))},indent=2)+"\n")
    return out


if __name__ == "__main__":
    try: print(f"Wrote {run(Path(__file__).resolve().parents[1])}")
    except (OSError,KeyError,ValueError,json.JSONDecodeError,ValueErrorModel) as exc:
        print(f"Production value model failed: {exc}",file=sys.stderr);raise SystemExit(1)
