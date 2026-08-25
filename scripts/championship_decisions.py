#!/usr/bin/env python3
"""Strategy-neutral completion paths, decision bands, and historical proxies."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.championship_equity import POSITIONS, canonical_players, lineup_score, pointer_payload
except ModuleNotFoundError:
    from championship_equity import POSITIONS, canonical_players, lineup_score, pointer_payload

REQUIRED_CURRENT = {"QB": 1, "WR": 2, "RB": 1, "TE": 1, "K": 1, "DEF": 1}
ROSTER_SIZE = 14


class DecisionModelError(RuntimeError):
    pass


def legal_roster(rows: list[dict[str, Any]], roster_size: int = ROSTER_SIZE) -> bool:
    counts = Counter(row["position"] for row in rows)
    return len(rows) == roster_size and all(counts[position] >= count for position, count in REQUIRED_CURRENT.items()) and counts["WR"] + counts["RB"] >= 4 and counts["WR"] + counts["RB"] + counts["TE"] >= 6


def completion_path(partial: list[dict[str, Any]], candidates: list[dict[str, Any]], budget: float,
                    price_key: str, objective: str = "lineup") -> dict[str, Any] | None:
    """Greedily complete a legal roster without encoding a named construction style."""
    if len(partial) > ROSTER_SIZE or sum(float(row[price_key]) for row in partial) > budget: return None
    chosen=list(partial); used={row["internal_player_id"] for row in chosen}
    available=[row for row in candidates if row["internal_player_id"] not in used and row["position"] in POSITIONS]
    def utility(row: dict[str, Any]) -> float:
        points=float(row.get("projected_points",0)); price=max(1.0,float(row[price_key]))
        if objective == "efficiency": return points/price
        if objective == "ceiling": return (points + float(row.get("production_value_high",0))*1.5)/(price**0.5)
        return points/(price**0.65)
    def can_add(row: dict[str, Any]) -> bool:
        remaining=ROSTER_SIZE-len(chosen)-1; spend=sum(float(item[price_key]) for item in chosen)+float(row[price_key])
        return spend + remaining <= budget
    def add_best(position_set: set[str]) -> bool:
        options=[row for row in available if row["position"] in position_set and can_add(row)]
        if not options:return False
        best=max(options,key=lambda row:(utility(row),-float(row[price_key]),row["internal_player_id"]));chosen.append(best);available.remove(best);return True
    counts=Counter(row["position"] for row in chosen)
    for position,minimum in REQUIRED_CURRENT.items():
        for _ in range(max(0,minimum-counts[position])):
            if not add_best({position}):return None
    while sum(1 for row in chosen if row["position"] in {"WR","RB"}) < 4:
        if not add_best({"WR","RB"}):return None
    while sum(1 for row in chosen if row["position"] in {"WR","RB","TE"}) < 6:
        if not add_best({"WR","RB","TE"}):return None
    while len(chosen)<ROSTER_SIZE:
        if not add_best(set(POSITIONS)):return None
    if not legal_roster(chosen):return None
    spend=sum(float(row[price_key]) for row in chosen)
    weekly_points=15*lineup_score([{"position":row["position"],"points":float(row.get("projected_points",0))/16} for row in chosen])
    return {"objective":objective,"spend":round(spend,2),"unspent":round(budget-spend,2),"projected_regular_lineup_points":round(weekly_points,2),
        "players":[{"internal_player_id":row["internal_player_id"],"player_name":row["player_name"],"position":row["position"],"price":round(float(row[price_key]),2)} for row in chosen]}


def decision_band(scenario_deltas: list[float], simulation_half_width: float = 0.01) -> dict[str, Any]:
    """Translate robust championship-equity deltas to restrained action bands."""
    if not scenario_deltas: raise DecisionModelError("At least one scenario delta is required")
    ordered=sorted(scenario_deltas); median=statistics.median(ordered); favorable=sum(value>0 for value in ordered)/len(ordered)
    robust_low=ordered[max(0,math.floor(0.2*(len(ordered)-1)))]; robust_high=ordered[min(len(ordered)-1,math.ceil(0.8*(len(ordered)-1)))]
    noise=max(0.005,simulation_half_width); strong=max(0.03,2*noise); lean=max(0.0125,1.25*noise)
    if median>=strong and robust_low>0 and favorable>=0.8: band="strong_pursue"
    elif median>=lean and favorable>=2/3: band="lean_pursue"
    elif median<=-strong and robust_high<0 and favorable<=0.2: band="strong_pass"
    elif median<=-lean and favorable<=1/3: band="lean_pass"
    else: band="neutral"
    return {"band":band,"median_championship_equity_delta":round(median,4),"scenario_positive_rate":round(favorable,4),
        "robust_range":[round(robust_low,4),round(robust_high,4)],"noise_floor":round(noise,4)}


def price_controlled_replay(sales: list[dict[str, Any]], projected: list[dict[str, Any]], actual_weekly: list[dict[str, Any]], season: int) -> dict[str, Any]:
    """Compare purchases with cheaper same-position options; not a chronology replay."""
    projections={row["internal_player_id"]:float(row["projected_points"]) for row in projected}
    actual=defaultdict(float)
    for row in actual_weekly:
        if int(row["season"])==season and int(row["week"])<=15:actual[row["internal_player_id"]]+=float(row["league_points"])
    season_sales=[row for row in sales if int(row["season"])==season and row["position"] in POSITIONS and row["internal_player_id"] in projections]
    decisions=[]
    for bought in season_sales:
        alternatives=[row for row in season_sales if row["position"]==bought["position"] and row["salary"]<=bought["salary"] and row["internal_player_id"]!=bought["internal_player_id"]]
        if not alternatives:continue
        alternative=max(alternatives,key=lambda row:(projections.get(row["internal_player_id"],-1),-row["salary"]))
        predicted_delta=projections[bought["internal_player_id"]]-projections.get(alternative["internal_player_id"],0)
        actual_delta=actual[bought["internal_player_id"]]-actual[alternative["internal_player_id"]]
        decisions.append({"owner":bought["owner"],"bought":bought["player_name"],"alternative":alternative["player_name"],"position":bought["position"],
            "bought_price":bought["salary"],"alternative_price":alternative["salary"],"projected_points_delta":round(predicted_delta,2),"actual_points_delta":round(actual_delta,2),
            "projection_direction_correct":(predicted_delta>=0)==(actual_delta>=0)})
    return {"season":season,"decisions":decisions}


def run(root: Path) -> Path:
    board_pointer=json.loads((root/"data/processed/production_value_model/latest.json").read_text());board_path=root/board_pointer["decision_board_json"]
    board=json.loads(board_path.read_text())["players"]
    auction,auction_path=pointer_payload(root,"data/processed/auction_history_matches/latest.json")
    equity_pointer=json.loads((root/"data/processed/championship_equity/latest.json").read_text());equity_path=root/equity_pointer["historical_backtest"]
    equity_summary=json.loads(equity_path.read_text())["summary"];stability=equity_summary["simulation_seed_stability"]
    calibrated_noise=max(0.01,float(stability["max_owner_range"])/2)
    required_simulations=math.ceil(float(stability["simulations_per_seed"])*(float(stability["max_owner_range"])/0.01)**2)
    nfl_pointer=json.loads((root/"data/processed/nflverse/latest.json").read_text());actual_path=(root/nfl_pointer["manifest"]).parent/"league_scored_actuals.json";actual=json.loads(actual_path.read_text())
    price_scenarios={"favorable":"price_range_low","expected":"expected_jugg_price","adverse":"price_range_high"}
    objectives=("lineup","efficiency","ceiling");completion_rows=[]
    targets=sorted([row for row in board if row.get("draft_probability",0)>=0.25],key=lambda row:-row.get("production_value",0))
    for target in targets:
        scenarios={}
        for scenario,price_key in price_scenarios.items():
            paths=[completion_path([{**target}],board,200,price_key,objective) for objective in objectives]
            scenarios[scenario]=[path for path in paths if path]
        completion_rows.append({"internal_player_id":target["internal_player_id"],"player_name":target["player_name"],"position":target["position"],"scenarios":scenarios})
    replays=[]
    for season in range(2020,2026):
        projected,_=canonical_players(root,season);replays.append(price_controlled_replay(auction["sales"],projected,actual["weekly"],season))
    decisions=[row for season in replays for row in season["decisions"]]
    correct=sum(row["projection_direction_correct"] for row in decisions)
    replay_summary={"decision_count":len(decisions),"directional_accuracy":round(correct/len(decisions),4) if decisions else None,
        "scope":"Price-controlled same-position substitution proxy. Historical auction chronology and true availability are unknown."}
    band_examples={"strong_pursue":decision_band([.035,.041,.032,.045,.038],calibrated_noise),"lean_pursue":decision_band([.018,.021,.024,.02,.022],calibrated_noise),
        "neutral":decision_band([-.01,.005,.012,-.004,.008],calibrated_noise),"lean_pass":decision_band([-.018,-.021,-.024,-.02,-.022],calibrated_noise),"strong_pass":decision_band([-.035,-.041,-.032,-.045,-.038],calibrated_noise)}
    built=datetime.now(timezone.utc);build_id=built.strftime("%Y%m%dT%H%M%SZ");out=root/"data/processed/championship_decisions"/build_id;out.mkdir(parents=True,exist_ok=True)
    metadata={"schema_version":1,"build_id":build_id,"strategy_neutral":True,"inputs":{str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (board_path,auction_path,actual_path,equity_path)}}
    (out/"completion_paths_2026.json").write_text(json.dumps({"metadata":metadata,"price_scenarios":price_scenarios,"objectives":objectives,"targets":completion_rows},indent=2,sort_keys=True)+"\n")
    (out/"historical_decision_proxy.json").write_text(json.dumps({"metadata":metadata,"summary":replay_summary,"seasons":replays},indent=2,sort_keys=True)+"\n")
    (out/"decision_band_contract.json").write_text(json.dumps({"metadata":metadata,"bands":["strong_pursue","lean_pursue","neutral","lean_pass","strong_pass"],"examples":band_examples,
        "calibration":{"observed_max_seed_range":stability["max_owner_range"],"simulations_per_seed":stability["simulations_per_seed"],
            "decision_noise_floor":round(calibrated_noise,4),"estimated_simulations_for_one_point_max_range":required_simulations},
        "rule":"Bands require magnitude beyond simulation noise and agreement across reasonable scenarios; neutral is the default."},indent=2,sort_keys=True)+"\n")
    latest=root/"data/processed/championship_decisions/latest.json";latest.write_text(json.dumps({"schema_version":1,"build_id":build_id,"completion_paths":str((out/'completion_paths_2026.json').relative_to(root)),"historical_decision_proxy":str((out/'historical_decision_proxy.json').relative_to(root)),"decision_band_contract":str((out/'decision_band_contract.json').relative_to(root))},indent=2)+"\n")
    return out


if __name__=="__main__": print(f"Wrote {run(Path(__file__).resolve().parents[1])}")
