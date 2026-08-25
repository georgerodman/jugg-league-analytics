#!/usr/bin/env python3
"""Build standalone player-week, lineup, and schedule-neutral equity artifacts."""

from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.fantasypros_projections import score_player
except ModuleNotFoundError:  # Direct `python scripts/championship_equity.py` execution.
    from fantasypros_projections import score_player

POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")
CURRENT_SKILL_SLOTS = (("WR",), ("WR",), ("RB",), ("TE",), ("WR", "RB"), ("WR", "RB", "TE"))
HISTORICAL_SKILL_SLOTS = (("WR",), ("WR",), ("RB",), ("TE",), ("WR", "RB"))
REGULAR_WEEKS = tuple(range(1, 16))
PLAYOFF_WEEKS = (16, 17)
SEED = 20260823


class EquityModelError(RuntimeError):
    pass


def pointer_payload(root: Path, pointer_path: str, key: str = "artifact") -> tuple[dict[str, Any], Path]:
    pointer = json.loads((root / pointer_path).read_text())
    path = root / pointer[key]
    return json.loads(path.read_text()), path


def lineup_score(players: list[dict[str, Any]], points_key: str = "points", current_format: bool = True) -> float:
    """Return the maximum legal starter score without using hindsight across weeks."""
    fixed_points = 0.0
    for position in ("QB", "K", "DEF"):
        fixed_points += max((float(row.get(points_key, 0.0)) for row in players if row["position"] == position), default=0.0)
    skill = [row for row in players if row["position"] in {"RB", "WR", "TE"}]
    def required_score(excluded: set[int]) -> float | None:
        available = [(index, row) for index, row in enumerate(skill) if index not in excluded]
        wr = sorted((float(row.get(points_key, 0.0)) for _, row in available if row["position"] == "WR"), reverse=True)
        rb = sorted((float(row.get(points_key, 0.0)) for _, row in available if row["position"] == "RB"), reverse=True)
        te = sorted((float(row.get(points_key, 0.0)) for _, row in available if row["position"] == "TE"), reverse=True)
        return sum(wr[:2]) + rb[0] + te[0] if len(wr) >= 2 and rb and te else None
    best = 0.0
    first_flex = [(index, row) for index, row in enumerate(skill) if row["position"] in {"WR", "RB"}]
    if current_format:
        second_flex = list(enumerate(skill))
        for left_index, left in first_flex:
            for right_index, right in second_flex:
                if left_index == right_index: continue
                base = required_score({left_index, right_index})
                if base is not None: best = max(best, base + float(left.get(points_key, 0.0)) + float(right.get(points_key, 0.0)))
    else:
        for index, flex in first_flex:
            base = required_score({index})
            if base is not None: best = max(best, base + float(flex.get(points_key, 0.0)))
    return round(fixed_points + best, 4)


def position_volatility(actual_weekly: list[dict[str, Any]]) -> dict[str, float]:
    """Median within-player-season active-week CV, avoiding talent-level mixing."""
    grouped: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for row in actual_weekly:
        if row["position"] in POSITIONS and float(row["league_points"]) > 0:
            grouped[(row["position"], row["internal_player_id"], int(row["season"]))].append(float(row["league_points"]))
    values: dict[str, list[float]] = defaultdict(list)
    for (position, _, _), rows in grouped.items():
        if len(rows) >= 6 and statistics.fmean(rows) > 0:
            values[position].append(statistics.pstdev(rows) / statistics.fmean(rows))
    result = {}
    for position in POSITIONS:
        rows = values[position]
        if not rows: raise EquityModelError(f"No volatility samples for {position}")
        result[position] = round(min(1.25, max(0.15, statistics.median(rows))), 4)
    return result


def team_byes(schedule_rows: list[dict[str, str]], season: int) -> dict[str, int]:
    games: dict[str, set[int]] = defaultdict(set)
    for row in schedule_rows:
        if int(row["season"]) == season and row["game_type"] == "REG" and int(row["week"]) <= 17:
            games[row["home_team"]].add(int(row["week"])); games[row["away_team"]].add(int(row["week"]))
    return {team: next((week for week in range(1, 18) if week not in weeks), 0) for team, weeks in games.items()}


def schedule_opponents(schedule_rows: list[dict[str, str]], season: int) -> dict[tuple[str, int], str]:
    result = {}
    for row in schedule_rows:
        if int(row["season"]) == season and row["game_type"] == "REG" and int(row["week"]) <= 17:
            week = int(row["week"]); result[(row["home_team"], week)] = row["away_team"]; result[(row["away_team"], week)] = row["home_team"]
    return result


def calibrate_risk(actual_weekly: list[dict[str, Any]], sales: list[dict[str, Any]], target_season: int,
                   position_cv: dict[str, float]) -> tuple[dict[str, float], dict[str, float], dict[str, float]]:
    history = [row for row in actual_weekly if int(row["season"]) < target_season and int(row["week"]) <= 17 and row["position"] in POSITIONS]
    fallback_history = history or [row for row in actual_weekly if row["position"] in POSITIONS and int(row["week"]) <= 17]
    drafted = {(int(row["season"]), row["internal_player_id"], row["position"]) for row in sales if int(row["season"]) < target_season}
    position_presence: dict[str, list[float]] = defaultdict(list)
    by_player_season: dict[tuple[str, int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in fallback_history: by_player_season[(row["internal_player_id"], int(row["season"]), row["position"])].append(row)
    for (player_id, season, position), rows in by_player_season.items():
        if (season, player_id, position) in drafted:
            position_presence[position].append(min(1.0, len({int(row["week"]) for row in rows}) / 16))
    position_availability = {position: round(statistics.fmean(position_presence[position]), 4) if position_presence[position] else 0.9 for position in POSITIONS}
    player_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in history: player_rows[row["internal_player_id"]].append(row)
    availability, cvs = {}, {}
    for player_id, rows in player_rows.items():
        position = rows[-1]["position"]; seasons = {int(row["season"]) for row in rows}
        observed = len({(int(row["season"]), int(row["week"])) for row in rows}); expected = 16 * len(seasons)
        raw_availability = min(1.0, observed / expected) if expected else position_availability[position]
        weight = expected / (expected + 32); availability[player_id] = round(weight*raw_availability + (1-weight)*position_availability[position], 4)
        season_cvs=[]
        for season in seasons:
            values=[float(row["league_points"]) for row in rows if int(row["season"])==season and float(row["league_points"])>0]
            if len(values)>=6 and statistics.fmean(values)>0: season_cvs.append(statistics.pstdev(values)/statistics.fmean(values))
        if season_cvs:
            count=sum(1 for row in rows if float(row["league_points"])>0); weight=count/(count+24)
            cvs[player_id]=round(weight*statistics.fmean(season_cvs)+(1-weight)*position_cv[position],4)
    return availability, cvs, position_availability


def opponent_factors(actual_weekly: list[dict[str, Any]], schedule_rows: list[dict[str, str]], target_season: int) -> dict[tuple[str, str], float]:
    opponents={(int(row["season"]), team, int(row["week"])): opponent for row in schedule_rows if int(row["season"])<target_season and row["game_type"]=="REG" and int(row["week"])<=17 for team,opponent in ((row["home_team"],row["away_team"]),(row["away_team"],row["home_team"]))}
    groups: dict[tuple[str,int,str],list[float]]=defaultdict(list)
    for row in actual_weekly:
        if int(row["season"])<target_season and row["position"] in POSITIONS and float(row["league_points"])>0:
            groups[(row["internal_player_id"],int(row["season"]),row["position"])].append(float(row["league_points"]))
    means={key:statistics.fmean(values) for key,values in groups.items() if len(values)>=4}
    ratios:dict[tuple[str,str],list[float]]=defaultdict(list)
    for row in actual_weekly:
        key=(row["internal_player_id"],int(row["season"]),row["position"]); mean=means.get(key)
        opponent=opponents.get((int(row["season"]),row.get("team"),int(row["week"])))
        if mean and opponent and float(row["league_points"])>0: ratios[(opponent,row["position"])].append(float(row["league_points"])/mean)
    result={}
    for key,values in ratios.items():
        weight=len(values)/(len(values)+100); result[key]=round(min(1.15,max(0.85,1+weight*(statistics.fmean(values)-1))),4)
    return result


def weekly_projection_rows(players: list[dict[str, Any]], byes: dict[str, int], volatility: dict[str, float], season: int,
                           availability: dict[str, float] | None = None, player_cv: dict[str, float] | None = None,
                           opponents: dict[tuple[str, int], str] | None = None,
                           defense_factors: dict[tuple[str, str], float] | None = None) -> list[dict[str, Any]]:
    availability = availability or {}; player_cv = player_cv or {}; opponents = opponents or {}; defense_factors = defense_factors or {}
    rows = []
    for player in players:
        points = player.get("projected_points")
        if points is None or player["position"] not in POSITIONS:
            continue
        bye = int(player.get("bye_week") or byes.get(player.get("nfl_team"), 0) or 0)
        active = [week for week in range(1, 18) if week != bye]
        shapes = {week: defense_factors.get((opponents.get((player.get("nfl_team"), week), ""), player["position"]), 1.0) for week in active}
        shape_total = sum(shapes.values()) or len(active)
        active_probability = min(0.995, max(0.5, availability.get(player["internal_player_id"], 0.92)))
        cv = player_cv.get(player["internal_player_id"], volatility[player["position"]])
        for week in range(1, 18):
            mean = 0.0 if week == bye else float(points) * shapes[week] / shape_total
            rows.append({"season": season, "week": week, "internal_player_id": player["internal_player_id"],
                "player_name": player["player_name"], "position": player["position"], "nfl_team": player.get("nfl_team"),
                "bye_week": bye or None, "opponent": opponents.get((player.get("nfl_team"), week)),
                "opponent_factor": 0.0 if week == bye else round(shapes[week], 4), "projected_points": round(mean, 4),
                "active_game_projected_points": 0.0 if week == bye else round(mean / active_probability, 4),
                "availability_probability": 0.0 if week == bye else round(active_probability, 4),
                "weekly_cv": round(cv, 4), "projection_source": "season_anchor_opponent_shaped_reconciled"})
    return rows


def draw_points(mean: float, cv: float, rng: random.Random, availability_probability: float = 1.0) -> float:
    if mean <= 0:
        return 0.0
    if rng.random() > availability_probability:
        return 0.0
    sigma2 = math.log(1 + cv * cv); sigma = math.sqrt(sigma2); mu = math.log(mean) - sigma2 / 2
    return rng.lognormvariate(mu, sigma)


def roster_week_score(roster: list[dict[str, Any]], week: int, rng: random.Random, current_format: bool = True,
                      team_factors: dict[str, float] | None = None) -> float:
    team_factors = team_factors or {}
    rows = []
    for row in roster:
        weekly = row["weekly"][week]
        active_mean = float(weekly.get("active_mean", weekly.get("mean", 0.0)))
        availability = float(weekly.get("availability", 1.0))
        draw = draw_points(active_mean, float(weekly.get("cv", 0.5)), rng, availability)
        if row.get("position") != "DEF":
            draw *= team_factors.get(row.get("nfl_team", ""), 1.0)
        rows.append({**row, "draw": draw})
    return lineup_score(rows, "draw", current_format)


def wilson_interval(successes: int, trials: int, z: float = 1.644854) -> list[float]:
    if trials <= 0: return [0.0, 0.0]
    p = successes / trials; denominator = 1 + z*z/trials
    center = (p + z*z/(2*trials)) / denominator
    margin = z * math.sqrt(p*(1-p)/trials + z*z/(4*trials*trials)) / denominator
    return [round(max(0.0, center-margin), 4), round(min(1.0, center+margin), 4)]


def simulate_league(rosters: dict[str, list[dict[str, Any]]], simulations: int = 1000, seed: int = SEED, current_format: bool = True) -> dict[str, Any]:
    if len(rosters) != 10:
        raise EquityModelError(f"Expected 10 teams, received {len(rosters)}")
    rng = random.Random(seed); teams = sorted(rosters); playoffs = defaultdict(int); titles = defaultdict(int); points_sum = defaultdict(float)
    for _ in range(simulations):
        nfl_teams = {row.get("nfl_team") for roster in rosters.values() for row in roster if row.get("nfl_team")}
        shared = {week: {team: draw_points(1.0, 0.12, rng) for team in nfl_teams} for week in range(1, 18)}
        scores = {team: {week: roster_week_score(rosters[team], week, rng, current_format, shared[week]) for week in range(1, 18)} for team in teams}
        wins = defaultdict(int)
        for week in REGULAR_WEEKS:
            shuffled = teams[:]; rng.shuffle(shuffled)
            for left, right in zip(shuffled[::2], shuffled[1::2]):
                if scores[left][week] > scores[right][week]: wins[left] += 1
                elif scores[right][week] > scores[left][week]: wins[right] += 1
                else: wins[left] += 0.5; wins[right] += 0.5
        regular_points = {team: sum(scores[team][week] for week in REGULAR_WEEKS) for team in teams}
        seeds = sorted(teams, key=lambda team: (-wins[team], -regular_points[team], team))[:4]
        for team in seeds: playoffs[team] += 1
        semifinalists = [(seeds[0], seeds[3]), (seeds[1], seeds[2])]
        finalists = [left if scores[left][16] >= scores[right][16] else right for left, right in semifinalists]
        champion = finalists[0] if scores[finalists[0]][17] >= scores[finalists[1]][17] else finalists[1]
        titles[champion] += 1
        for team in teams: points_sum[team] += regular_points[team]
    return {"simulations": simulations, "seed": seed, "teams": [{"team": team,
        "expected_regular_points": round(points_sum[team] / simulations, 2),
        "playoff_equity": round(playoffs[team] / simulations, 4),
        "playoff_equity_interval_90": wilson_interval(playoffs[team], simulations),
        "championship_equity": round(titles[team] / simulations, 4),
        "championship_equity_interval_90": wilson_interval(titles[team], simulations)} for team in teams],
        "correlation_assumption":"A mean-one weekly NFL-team factor with CV 0.12 is shared by offensive teammates."}


def canonical_players(root: Path, season: int, source: str = "fantasypros") -> tuple[list[dict[str, Any]], Path]:
    payload, path = pointer_payload(root, f"data/processed/canonical_projections/{season}/latest.json")
    league = json.loads((root / "config/league.json").read_text())
    rows = []
    for player in payload["players"]:
        fp = player.get("fantasypros", {}).get("league_projected_points")
        ffa_stats = player.get("enrichments", {}).get("ffa", {}).get("stats")
        ffa = score_player(player["position"], ffa_stats, league) if ffa_stats and player["position"] in {"QB","RB","WR","TE","K"} else None
        if source == "fantasypros": points = fp
        elif source == "ffa_fallback": points = ffa if ffa is not None else fp
        elif source == "ensemble": points = statistics.fmean([float(value) for value in (fp, ffa) if value is not None]) if fp is not None or ffa is not None else None
        else: raise EquityModelError(f"Unknown projection source {source}")
        if points is not None:
            rows.append({"internal_player_id": player["internal_player_id"], "player_name": player["name"],
                "position": player["position"], "nfl_team": player.get("nfl_team"), "projected_points": float(points)})
    return rows, path


def build_rosters(sales: list[dict[str, Any]], weekly_lookup: dict[tuple[str, int], dict[str, float]], season: int) -> dict[str, list[dict[str, Any]]]:
    rosters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sale in sales:
        if sale["season"] != season or sale["position"] not in POSITIONS:
            continue
        weekly = {week: weekly_lookup.get((sale["internal_player_id"], week), {"mean":0.0,"active_mean":0.0,"cv":0.5,"availability":0.9}) for week in range(1, 18)}
        rosters[sale["owner"]].append({"internal_player_id": sale["internal_player_id"], "position": sale["position"], "nfl_team": sale.get("nfl_team"), "salary": sale["salary"], "weekly": weekly})
    return dict(rosters)


def deterministic_roster_points(roster: list[dict[str, Any]], current_format: bool) -> float:
    return round(sum(lineup_score([{"position": row["position"], "points": row["weekly"][week]["mean"]} for row in roster], current_format=current_format) for week in REGULAR_WEEKS), 2)


def replacement_access_backtest(sales: list[dict[str, Any]], players: list[dict[str, Any]],
                                actual_lookup: dict[tuple[str, int], float], season: int,
                                max_adds: int = 4, trailing_weight: float = 0.3,
                                improvement_threshold: float = 1.20) -> list[dict[str, Any]]:
    """Apply a conservative waiver policy using preseason and prior-week data only."""
    season_sales = [row for row in sales if row["season"] == season and row["position"] in POSITIONS]
    drafted = {row["internal_player_id"] for row in season_sales}
    player_by_id = {row["internal_player_id"]: row for row in players}
    pool = {row["internal_player_id"] for row in players if row["internal_player_id"] not in drafted and row["position"] in POSITIONS}
    rosters: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for sale in season_sales:
        projection = player_by_id.get(sale["internal_player_id"], {})
        rosters[sale["owner"]].append({"internal_player_id":sale["internal_player_id"], "position":sale["position"],
            "player_name":sale.get("player_name", sale["internal_player_id"]), "projected_points":float(projection.get("projected_points", 0.0))})
    frozen = {owner:list(roster) for owner,roster in rosters.items()}; adds=defaultdict(int); moves=defaultdict(list)
    frozen_points=defaultdict(float); managed_points=defaultdict(float); owners=sorted(rosters)

    def signal(row: dict[str, Any], week: int) -> float:
        prior = float(row.get("projected_points", 0.0))/16
        observed = [actual_lookup.get((row["internal_player_id"], prior_week), 0.0) for prior_week in range(max(1, week-3), week)]
        return prior if not observed else (1-trailing_weight)*prior + trailing_weight*statistics.fmean(observed)

    for week in REGULAR_WEEKS:
        order = owners[week % len(owners):] + owners[:week % len(owners)]
        if week > 1:
            for owner in order:
                if adds[owner] >= max_adds: continue
                candidates = [player_by_id[player_id] for player_id in pool]
                best = None
                for incumbent in rosters[owner]:
                    same_position = [candidate for candidate in candidates if candidate["position"] == incumbent["position"]]
                    if not same_position: continue
                    candidate = max(same_position, key=lambda row: (signal(row, week), row["internal_player_id"]))
                    incumbent_signal=signal(incumbent,week); candidate_signal=signal(candidate,week)
                    recent=[actual_lookup.get((incumbent["internal_player_id"],w),0.0) for w in range(max(1,week-2),week)]
                    threshold=1.05 if len(recent)==2 and all(value==0 for value in recent) else improvement_threshold
                    gain=candidate_signal-incumbent_signal*threshold
                    if gain>0 and (best is None or gain>best[0]): best=(gain,incumbent,candidate,incumbent_signal,candidate_signal)
                if best:
                    _,incumbent,candidate,incumbent_signal,candidate_signal=best
                    rosters[owner].remove(incumbent); rosters[owner].append({**candidate}); pool.remove(candidate["internal_player_id"]); adds[owner]+=1
                    moves[owner].append({"week":week,"dropped":incumbent["player_name"],"added":candidate["player_name"],
                        "incumbent_signal":round(incumbent_signal,2),"candidate_signal":round(candidate_signal,2)})
        for owner in owners:
            frozen_points[owner]+=lineup_score([{"position":row["position"],"points":actual_lookup.get((row["internal_player_id"],week),0.0)} for row in frozen[owner]],current_format=season>=2025)
            managed_points[owner]+=lineup_score([{"position":row["position"],"points":actual_lookup.get((row["internal_player_id"],week),0.0)} for row in rosters[owner]],current_format=season>=2025)
    return [{"owner":owner,"frozen_actual_optimal_points":round(frozen_points[owner],2),
        "replacement_access_actual_optimal_points":round(managed_points[owner],2),
        "replacement_access_gain":round(managed_points[owner]-frozen_points[owner],2),"acquisitions":moves[owner]} for owner in owners]


def run(root: Path, simulations: int = 2500) -> Path:
    nfl_pointer = json.loads((root / "data/processed/nflverse/latest.json").read_text())
    nfl_dir = (root / nfl_pointer["manifest"]).parent
    actual_path = nfl_dir / "league_scored_actuals.json"; actual = json.loads(actual_path.read_text())
    volatility = position_volatility(actual["weekly"])
    schedule_path = nfl_dir / "schedules.csv"
    import csv
    with schedule_path.open(newline="", encoding="utf-8") as handle: schedules = list(csv.DictReader(handle))
    espn, espn_path = pointer_payload(root, "data/processed/espn_salary_cap_values/2026/latest.json")
    bye_by_id = {row["internal_player_id"]: row.get("bye_week") for row in espn["values"]}
    players_2026, projection_path = canonical_players(root, 2026)
    for row in players_2026: row["bye_week"] = bye_by_id.get(row["internal_player_id"])
    auction, auction_path = pointer_payload(root, "data/processed/auction_history_matches/latest.json")
    availability_2026, player_cv_2026, position_availability = calibrate_risk(actual["weekly"], auction["sales"], 2026, volatility)
    factors_2026 = opponent_factors(actual["weekly"], schedules, 2026)
    weekly_2026 = weekly_projection_rows(players_2026, team_byes(schedules, 2026), volatility, 2026, availability_2026,
        player_cv_2026, schedule_opponents(schedules, 2026), factors_2026)
    backtests = []; replacement_backtests=[]; replacement_stress={name:[] for name in ("frozen","limited","baseline","active")}; seed_stability={}
    source_pairs: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for season in range(2020, 2026):
        projected, _ = canonical_players(root, season)
        projection_by_id = {row["internal_player_id"]: row for row in projected}
        historical_byes = team_byes(schedules, season)
        historical_availability, historical_player_cv, _ = calibrate_risk(actual["weekly"], auction["sales"], season, volatility)
        projected_weekly = weekly_projection_rows(projected, historical_byes, volatility, season, historical_availability,
            historical_player_cv, schedule_opponents(schedules, season), opponent_factors(actual["weekly"], schedules, season))
        projected_lookup = {(row["internal_player_id"], row["week"]): {"mean":row["projected_points"],"active_mean":row["active_game_projected_points"],
            "cv":row["weekly_cv"],"availability":row["availability_probability"]} for row in projected_weekly}
        projected_rosters = build_rosters(auction["sales"], projected_lookup, season)
        if len(projected_rosters) != 10: continue
        sim = simulate_league(projected_rosters, simulations=simulations, seed=SEED + season, current_format=season >= 2025)
        if season == 2025:
            stability_runs=[simulate_league(projected_rosters,simulations=max(1000,simulations//3),seed=SEED+season+offset,current_format=True) for offset in (101,202,303,404,505)]
            by_owner={owner:[] for owner in projected_rosters}
            for result in stability_runs:
                for team in result["teams"]: by_owner[team["team"]].append(team["championship_equity"])
            seed_stability={"season":2025,"seeds":5,"simulations_per_seed":max(1000,simulations//3),
                "mean_owner_range":round(statistics.fmean(max(values)-min(values) for values in by_owner.values()),4),
                "max_owner_range":round(max(max(values)-min(values) for values in by_owner.values()),4)}
        actual_lookup = {(row["internal_player_id"], row["week"]): float(row["league_points"]) for row in actual["weekly"] if row["season"] == season}
        replacement_backtests.append({"season":season,"owners":replacement_access_backtest(auction["sales"],projected,actual_lookup,season)})
        for name,settings in {"frozen":(0,0.0,9.0),"limited":(2,0.2,1.25),"baseline":(4,0.3,1.20),"active":(8,0.5,1.10)}.items():
            replacement_stress[name].extend(replacement_access_backtest(auction["sales"],projected,actual_lookup,season,*settings))
        owner_actual = []
        for owner, roster in projected_rosters.items():
            sales = [row for row in auction["sales"] if row["season"] == season and row["owner"] == owner]
            weekly_scores = []
            for week in range(1, 18):
                rows = [{"position": sale["position"], "points": actual_lookup.get((sale["internal_player_id"], week), 0.0)} for sale in sales]
                weekly_scores.append(lineup_score(rows, current_format=season >= 2025))
            owner_actual.append({"owner": owner, "actual_regular_optimal_points": round(sum(weekly_scores[:15]), 2),
                "actual_week_16": weekly_scores[15], "actual_week_17": weekly_scores[16],
                "top_three_salary_share": round(sum(sorted((sale["salary"] for sale in sales), reverse=True)[:3]) / 200, 4)})
        sim_by_owner = {row["team"]: row for row in sim["teams"]}
        for row in owner_actual: row.update({"projected_deterministic_regular_points":deterministic_roster_points(projected_rosters[row["owner"]], season >= 2025),
            "projected_regular_points": sim_by_owner[row["owner"]]["expected_regular_points"],
            "projected_playoff_equity": sim_by_owner[row["owner"]]["playoff_equity"], "projected_championship_equity": sim_by_owner[row["owner"]]["championship_equity"]})
        for source in ("fantasypros","ffa_fallback","ensemble"):
            source_players,_=canonical_players(root,season,source); source_weekly=weekly_projection_rows(source_players,historical_byes,volatility,season,
                historical_availability,historical_player_cv,schedule_opponents(schedules,season),opponent_factors(actual["weekly"],schedules,season))
            source_lookup={(item["internal_player_id"],item["week"]):{"mean":item["projected_points"],"active_mean":item["active_game_projected_points"],"cv":item["weekly_cv"],"availability":item["availability_probability"]} for item in source_weekly}
            source_rosters=build_rosters(auction["sales"],source_lookup,season)
            for row in owner_actual:
                value=deterministic_roster_points(source_rosters[row["owner"]],season>=2025);row.setdefault("projection_source_regular_points",{})[source]=value
                source_pairs[source].append((value,row["actual_regular_optimal_points"]))
        backtests.append({"season": season, "owners": owner_actual})
    pairs = [(row["projected_deterministic_regular_points"], row["actual_regular_optimal_points"]) for season in backtests for row in season["owners"]]
    def corr(values: list[tuple[float, float]]) -> float:
        xs, ys = zip(*values); xm, ym = statistics.fmean(xs), statistics.fmean(ys)
        denominator = math.sqrt(sum((x-xm)**2 for x in xs) * sum((y-ym)**2 for y in ys))
        return round(sum((x-xm)*(y-ym) for x,y in values) / denominator, 4) if denominator else 0.0
    construction_rows=[row for season in backtests for row in season["owners"]]
    ordered=sorted(construction_rows,key=lambda row:row["top_three_salary_share"]);quartile_size=max(1,len(ordered)//4)
    construction_diagnostics=[]
    for index in range(4):
        rows=ordered[index*quartile_size:(index+1)*quartile_size] if index<3 else ordered[index*quartile_size:]
        construction_diagnostics.append({"spending_concentration_quartile":index+1,"owner_seasons":len(rows),
            "mean_top_three_salary_share":round(statistics.fmean(row["top_three_salary_share"] for row in rows),4),
            "mean_actual_optimal_points":round(statistics.fmean(row["actual_regular_optimal_points"] for row in rows),2),
            "mean_projected_championship_equity":round(statistics.fmean(row["projected_championship_equity"] for row in rows),4)})
    summary = {"season_count": len(backtests), "owner_seasons": len(pairs), "projected_vs_actual_optimal_points_correlation": corr(pairs),
        "position_weekly_cv": volatility, "simulations_per_season": simulations,"roster_construction_diagnostics":construction_diagnostics,
        "construction_note":"Descriptive quartiles of spending concentration only; no named strategy or concentration target enters model decisions.",
        "projection_source_roster_correlations":{source:corr(values) for source,values in source_pairs.items()},
        "simulation_seed_stability":seed_stability}
    replacement_rows=[row for season in replacement_backtests for row in season["owners"]]
    replacement_summary={"owner_seasons":len(replacement_rows),"mean_frozen_actual_optimal_points":round(statistics.fmean(row["frozen_actual_optimal_points"] for row in replacement_rows),2),
        "mean_replacement_access_actual_optimal_points":round(statistics.fmean(row["replacement_access_actual_optimal_points"] for row in replacement_rows),2),
        "mean_gain":round(statistics.fmean(row["replacement_access_gain"] for row in replacement_rows),2),
        "median_gain":round(statistics.median(row["replacement_access_gain"] for row in replacement_rows),2),
        "policy":"Maximum four exclusive same-position acquisitions per team; 70% preseason projection and 30% trailing-three-week performance; 20% improvement threshold, relaxed to 5% after two zero weeks; no future data."}
    stress_summary={name:{"owner_seasons":len(rows),"mean_points":round(statistics.fmean(row["replacement_access_actual_optimal_points"] for row in rows),2),
        "mean_gain_over_frozen":round(statistics.fmean(row["replacement_access_gain"] for row in rows),2)} for name,rows in replacement_stress.items()}
    replacement_summary["stress_scenarios"]=stress_summary
    built = datetime.now(timezone.utc); build_id = built.strftime("%Y%m%dT%H%M%SZ")
    out = root / "data/processed/championship_equity" / build_id; out.mkdir(parents=True, exist_ok=True)
    inputs = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest() for path in (actual_path, schedule_path, espn_path, projection_path, auction_path)}
    (out / "weekly_projections_2026.json").write_text(json.dumps({"metadata":{"schema_version":2,"build_id":build_id,"inputs":inputs,
        "weekly_allocation":"season_anchor_opponent_shaped_reconciled","position_weekly_cv":volatility,
        "position_availability_probability":position_availability,"player_specific_cv_count":len(player_cv_2026),
        "player_specific_availability_count":len(availability_2026),"opponent_factor_count":len(factors_2026)},"players":weekly_2026}, indent=2, sort_keys=True)+"\n")
    (out / "historical_backtest.json").write_text(json.dumps({"metadata":{"schema_version":1,"build_id":build_id},"summary":summary,"seasons":backtests}, indent=2, sort_keys=True)+"\n")
    (out / "replacement_access_backtest.json").write_text(json.dumps({"metadata":{"schema_version":1,"build_id":build_id},"summary":replacement_summary,"seasons":replacement_backtests}, indent=2, sort_keys=True)+"\n")
    latest = root / "data/processed/championship_equity/latest.json"
    latest.write_text(json.dumps({"schema_version":1,"build_id":build_id,"weekly_projections":str((out/'weekly_projections_2026.json').relative_to(root)),"historical_backtest":str((out/'historical_backtest.json').relative_to(root)),"replacement_access_backtest":str((out/'replacement_access_backtest.json').relative_to(root))}, indent=2)+"\n")
    return out


if __name__ == "__main__":
    try: print(f"Wrote {run(Path(__file__).resolve().parents[1])}")
    except (OSError, KeyError, ValueError, json.JSONDecodeError, EquityModelError) as exc:
        print(f"Championship equity model failed: {exc}")
        raise SystemExit(1)
