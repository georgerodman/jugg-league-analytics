#!/usr/bin/env python3
"""Build evidence-weighted JUGG owner tendency profiles from auction results."""

from __future__ import annotations

import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POSITIONS = ("QB", "RB", "WR", "TE", "K", "DEF")


def safe_mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def build_profiles(sales: list[dict[str, Any]], market_by_key: dict[tuple[int,str], dict[str,Any]] | None = None) -> list[dict[str, Any]]:
    market_by_key = market_by_key or {}
    owners = sorted({row["owner"] for row in sales}); seasons = sorted({row["season"] for row in sales})
    league_position_spend = Counter(); league_total = sum(row["salary"] for row in sales)
    league_position_count = Counter(row["position"] for row in sales)
    for row in sales: league_position_spend[row["position"]] += row["salary"]
    league_team_count = Counter(row["nfl_team"] for row in sales if row.get("nfl_team"))
    profiles = []
    for owner in owners:
        rows = [row for row in sales if row["owner"] == owner]
        yearly = {season:[row for row in rows if row["season"] == season] for season in seasons}
        yearly_spend = [sum(row["salary"] for row in values) for values in yearly.values()]
        position_profiles = {}
        for position in POSITIONS:
            pos_rows = [row for row in rows if row["position"] == position]
            spend_share = sum(row["salary"] for row in pos_rows) / sum(row["salary"] for row in rows)
            league_share = league_position_spend[position] / league_total
            annual_deviations = []
            for season, values in yearly.items():
                season_total = sum(row["salary"] for row in values)
                league_season = [row for row in sales if row["season"] == season]
                league_season_share = sum(row["salary"] for row in league_season if row["position"] == position) / sum(row["salary"] for row in league_season)
                annual_deviations.append(sum(row["salary"] for row in values if row["position"] == position)/season_total - league_season_share)
            deviation = spend_share - league_share
            sign_consistency = safe_mean([1.0 if value * deviation > 0 else 0.0 for value in annual_deviations]) if deviation else 0.0
            position_profiles[position] = {
                "players_per_draft": round(len(pos_rows)/len(seasons),2),
                "league_players_per_draft": round(league_position_count[position]/len(owners)/len(seasons),2),
                "spend_per_draft": round(sum(row["salary"] for row in pos_rows)/len(seasons),2),
                "spend_share": round(spend_share,4), "league_spend_share":round(league_share,4),
                "spend_share_deviation":round(deviation,4), "direction_consistency":round(sign_consistency,4),
                "signal": "overweights" if deviation >= .03 and sign_consistency >= .5 else "underweights" if deviation <= -.03 and sign_consistency >= .5 else "neutral",
            }
        top_three_shares=[]; one_dollar=[]; stars=[]; max_bids=[]
        for values in yearly.values():
            prices=sorted((row["salary"] for row in values),reverse=True); total=sum(prices)
            top_three_shares.append(sum(prices[:3])/total);one_dollar.append(sum(price==1 for price in prices));stars.append(sum(price>=30 for price in prices));max_bids.append(max(prices))
        player_years=defaultdict(list)
        for row in rows: player_years[row["internal_player_id"]].append(row)
        repeats=sorted(({"internal_player_id":pid,"player_name":values[-1]["player_name"],"seasons":sorted(row["season"] for row in values),"times_drafted":len(values)} for pid,values in player_years.items() if len(values)>=2),key=lambda x:(-x["times_drafted"],x["player_name"]))
        owner_teams=Counter(row["nfl_team"] for row in rows if row.get("nfl_team")); team_preferences=[]
        for team,count in owner_teams.items():
            league_rate=league_team_count[team]/sum(league_team_count.values()); shrunk=(count+20*league_rate)/(len(rows)+20)
            lift=shrunk/league_rate if league_rate else 0
            if count>=4 and lift>=1.25: team_preferences.append({"nfl_team":team,"players":count,"shrunk_lift":round(lift,2)})
        team_preferences.sort(key=lambda x:(-x["shrunk_lift"],-x["players"],x["nfl_team"]))
        market_residuals=[]; residual_by_position=defaultdict(list)
        for row in rows:
            market=market_by_key.get((row["season"],row["internal_player_id"]))
            if market and market.get("espn_salary_cap_value") not in (None,""):
                residual=row["salary"]-float(market["espn_salary_cap_value"]);market_residuals.append(residual);residual_by_position[row["position"]].append(residual)
        profiles.append({"owner":owner,"seasons":len(seasons),"purchases":len(rows),"evidence_strength":"high",
            "spending":{"average_total":round(safe_mean(yearly_spend),2),"average_unused_budget":round(safe_mean([200-x for x in yearly_spend]),2),"average_max_bid":round(safe_mean(max_bids),2),"average_top_three_spend_share":round(safe_mean(top_three_shares),4),"average_30_plus_players":round(safe_mean(stars),2),"average_one_dollar_players":round(safe_mean(one_dollar),2)},
            "construction_style":"stars_and_scrubs" if safe_mean(top_three_shares)>=.62 and safe_mean(one_dollar)>=3 else "balanced" if safe_mean(top_three_shares)<=.48 else "mixed",
            "market_behavior":{"covered_purchases":len(market_residuals),"average_salary_minus_espn":round(safe_mean(market_residuals),2),"five_plus_overpay_rate":round(safe_mean([x>=5 for x in market_residuals]),4),"five_plus_underpay_rate":round(safe_mean([x<=-5 for x in market_residuals]),4),"average_residual_by_position":{p:round(safe_mean(residual_by_position[p]),2) for p in POSITIONS if residual_by_position[p]}},
            "positions":position_profiles,"repeat_players":repeats,"repeat_player_count":len(repeats),"nfl_team_preferences":team_preferences,
            "limitations":["No nomination order or purchase timing is available.","Preferences are probabilistic historical context, not intent."]})
    return profiles


def markdown_report(profiles: list[dict[str, Any]], build_id: str) -> str:
    lines = ["# JUGG Owner Tendency Report", "", f"Build: `{build_id}`", "",
        "These profiles summarize 2020–2025 final auction results. They describe probabilistic historical patterns, not owner intent. Nomination order and purchase timing are unavailable.", "",
        "## League summary", "", "| Owner | Construction | Strongest positional tendencies |", "| --- | --- | --- |"]
    for profile in profiles:
        signals=[f"{position} {values['signal']}" for position,values in profile["positions"].items() if values["signal"]!="neutral"]
        lines.append(f"| {profile['owner']} | {profile['construction_style'].replace('_',' ').title()} | {', '.join(signals) if signals else 'No threshold signal'} |")
    stylistic=[]; personnel=[]
    for profile in profiles:
        for position,values in profile["positions"].items():
            if values["signal"]!="neutral" and values["direction_consistency"]>=.999:
                stylistic.append(f"{profile['owner']} {values['signal']} {position} spending in all six seasons ({values['spend_share_deviation']:+.1%} spend-share deviation).")
        for repeat in profile["repeat_players"]:
            if repeat["times_drafted"]>=3:
                personnel.append(f"{profile['owner']} drafted {repeat['player_name']} in {repeat['times_drafted']} seasons.")
        for team in profile["nfl_team_preferences"]:
            if team["players"]>=8:
                personnel.append(f"{profile['owner']} drafted {team['players']} players from {team['nfl_team']} ({team['shrunk_lift']:.2f}× shrunken lift).")
    lines.extend(["", "## Strong stylistic trends", ""])
    lines.extend(f"- {signal}" for signal in stylistic)
    lines.extend(["", "## Strong personnel trends", ""])
    lines.extend(f"- {signal}" for signal in personnel)
    lines.extend(["", "Strong stylistic trends require six-of-six positional direction. Strong personnel trends require a player drafted in at least three seasons or at least eight purchases from one NFL team. They remain descriptive rather than deterministic.", "", "## Full owner writeups", ""])
    for profile in profiles:
        spending=profile["spending"]; market=profile["market_behavior"]
        lines.extend([f"## {profile['owner']}", "",
            f"**Construction:** {profile['construction_style'].replace('_',' ')}. Average spend was ${spending['average_total']:.2f}, with a ${spending['average_max_bid']:.2f} average maximum purchase. The top three purchases consumed {spending['average_top_three_spend_share']:.1%} of budget; the roster averaged {spending['average_30_plus_players']:.2f} players at $30+ and {spending['average_one_dollar_players']:.2f} one-dollar players.", ""])
        signals=[f"{position} {values['signal']} ({values['spend_share_deviation']:+.1%} spend share versus league; {values['direction_consistency']:.0%} directional consistency)" for position,values in profile["positions"].items() if values["signal"]!="neutral"]
        lines.append("**Positions:** "+("; ".join(signals)+"." if signals else "No position cleared the conservative tendency threshold."));lines.append("")
        lines.append(f"**Market behavior:** Across {market['covered_purchases']} ESPN-covered purchases, average salary was {market['average_salary_minus_espn']:+.2f} dollars versus ESPN. Purchases were $5+ above ESPN {market['five_plus_overpay_rate']:.1%} of the time and $5+ below ESPN {market['five_plus_underpay_rate']:.1%} of the time.");lines.append("")
        repeats=profile["repeat_players"][:6]
        lines.append("**Repeat players:** "+(", ".join(f"{row['player_name']} ({row['times_drafted']} drafts)" for row in repeats)+"." if repeats else "No player was drafted in multiple seasons."));lines.append("")
        teams=profile["nfl_team_preferences"][:5]
        lines.append("**Possible NFL-team affinities:** "+(", ".join(f"{row['nfl_team']} ({row['players']} purchases, {row['shrunk_lift']:.2f}× shrunken lift)" for row in teams)+"." if teams else "No team cleared the evidence threshold."));lines.extend(["", "---", ""])
    return "\n".join(lines)


def run(root: Path) -> Path:
    pointer=json.loads((root/"data/processed/auction_history_matches/latest.json").read_text()); source=root/pointer["artifact"]
    sales=json.loads(source.read_text())["sales"]
    price_pointer=json.loads((root/"data/processed/auction_price_model/latest.json").read_text())
    with (root/price_pointer["training_rows"]).open(newline="",encoding="utf-8") as f:
        market_rows=list(csv.DictReader(f))
    market_by_key={(int(row["season"]),row["internal_player_id"]):row for row in market_rows}
    profiles=build_profiles(sales,market_by_key)
    built=datetime.now(timezone.utc); build_id=built.strftime("%Y%m%dT%H%M%SZ"); out=root/"data/processed/owner_tendencies"/build_id;out.mkdir(parents=True,exist_ok=True)
    payload={"metadata":{"schema_version":1,"build_id":build_id,"built_at":built.isoformat(),"source":str(source.relative_to(root)),"owner_count":len(profiles),"seasons":sorted({row["season"] for row in sales}),"timing_features_available":False},"owners":profiles}
    path=out/"owner_profiles.json";path.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
    markdown_path=out/"owner_profiles.md";markdown_path.write_text(markdown_report(profiles,build_id)+"\n")
    fields=["owner","construction_style","average_total","average_unused_budget","average_max_bid","average_top_three_spend_share","average_30_plus_players","average_one_dollar_players","average_salary_minus_espn","five_plus_overpay_rate","five_plus_underpay_rate","repeat_player_count","position_signals","team_preferences"]
    with (out/"owner_profiles.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for p in profiles:w.writerow({"owner":p["owner"],"construction_style":p["construction_style"],**p["spending"],"average_salary_minus_espn":p["market_behavior"]["average_salary_minus_espn"],"five_plus_overpay_rate":p["market_behavior"]["five_plus_overpay_rate"],"five_plus_underpay_rate":p["market_behavior"]["five_plus_underpay_rate"],"repeat_player_count":p["repeat_player_count"],"position_signals":";".join(f"{k}:{v['signal']}" for k,v in p["positions"].items() if v["signal"]!="neutral"),"team_preferences":";".join(x["nfl_team"] for x in p["nfl_team_preferences"])})
    latest=root/"data/processed/owner_tendencies/latest.json";latest.write_text(json.dumps({"schema_version":1,"build_id":build_id,"artifact":str(path.relative_to(root)),"csv":str((out/"owner_profiles.csv").relative_to(root)),"markdown":str(markdown_path.relative_to(root))},indent=2)+"\n")
    return path


if __name__=="__main__":
    try:print(f"Wrote {run(Path(__file__).resolve().parents[1])}")
    except (OSError,KeyError,ValueError,json.JSONDecodeError) as exc:print(f"Owner tendency build failed: {exc}",file=sys.stderr);raise SystemExit(1)
