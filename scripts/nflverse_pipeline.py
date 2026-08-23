#!/usr/bin/env python3
"""Acquire nflverse data and publish normalized identities and league-scored actuals."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:  # Support both `python scripts/...` and imports from the test suite.
    from .build_canonical_projections import normalize_name, normalize_position, normalize_team
    from .fantasypros_projections import atomic_write
except ImportError:
    from build_canonical_projections import normalize_name, normalize_position, normalize_team
    from fantasypros_projections import atomic_write

SCHEMA_VERSION = 1
DEFAULT_SEASONS = tuple(range(2020, 2026))
BASE = "https://github.com/nflverse/nflverse-data/releases/download"
DATASETS = {
    "players": f"{BASE}/players/players.csv",
    "player_stats": f"{BASE}/stats_player/stats_player_week_{{season}}.csv",
    "rosters": f"{BASE}/rosters/roster_{{season}}.csv",
    "team_stats": f"{BASE}/stats_team/stats_team_week_{{season}}.csv",
    "schedules": "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
}
REQUIRED_COLUMNS = {
    "players": {"gsis_id", "display_name", "position", "espn_id"},
    "player_stats": {"player_id", "player_display_name", "position", "season", "week", "season_type"},
    "rosters": {"season", "team", "full_name", "position", "gsis_id", "yahoo_id"},
    "team_stats": {"season", "week", "team", "season_type", "def_sacks", "def_interceptions"},
    "schedules": {"season", "week", "game_type", "home_team", "away_team", "home_score", "away_score"},
}
PLAYER_STATS = (
    "completions", "attempts", "passing_yards", "passing_tds", "passing_interceptions",
    "passing_2pt_conversions", "carries", "rushing_yards", "rushing_tds",
    "rushing_2pt_conversions", "receptions", "targets", "receiving_yards", "receiving_tds",
    "receiving_2pt_conversions", "special_teams_tds", "fumbles_lost_total",
    "fg_made", "fg_att", "fg_missed", "fg_made_0_19", "fg_made_20_29", "fg_made_30_39",
    "fg_made_40_49", "fg_made_50_59", "fg_made_60_", "fg_missed_0_19",
    "fg_missed_20_29", "fg_missed_30_39", "fg_missed_40_49", "pat_made", "pat_missed",
)
TEAM_DEF_STATS = (
    "def_sacks", "def_interceptions", "fumble_recovery_opp", "def_tds", "def_safeties",
    "def_punt_blocks", "def_pat_blocks", "def_fg_blocks", "special_teams_tds",
)


class NflverseError(RuntimeError):
    pass


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"Accept": "text/csv", "User-Agent": "jugg-league-analytics/1"})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise NflverseError(f"Failed to download {url}: {exc}") from exc
    if not body or b"," not in body[:4096]:
        raise NflverseError(f"Downloaded data is empty or not CSV: {url}")
    return body


def csv_rows(body: bytes, dataset: str) -> list[dict[str, str]]:
    text = body.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    fields = set(reader.fieldnames or [])
    missing = REQUIRED_COLUMNS[dataset] - fields
    if missing:
        raise NflverseError(f"{dataset} schema is missing columns: {sorted(missing)}")
    rows = list(reader)
    if not rows:
        raise NflverseError(f"{dataset} contains no records")
    return rows


def number(row: dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value in {"", "NA", "N/A", "null", None}:
        return 0.0
    return float(value)


def clean_id(value: str | None) -> str | None:
    return None if value in {None, "", "NA", "N/A"} else str(value)


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str]) -> None:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    atomic_write(path, buffer.getvalue().encode())


def acquire(root: Path, seasons: tuple[int, ...], identity_seasons: tuple[int, ...] = ()) -> Path:
    fetched_at = datetime.now(timezone.utc)
    snapshot_id = fetched_at.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = root / "data" / "raw" / "nflverse" / snapshot_id
    requests: list[dict[str, Any]] = []
    targets = [("players", None), ("schedules", None)]
    targets.extend((dataset, season) for season in seasons for dataset in ("player_stats", "rosters", "team_stats"))
    targets.extend(("rosters", season) for season in identity_seasons if season not in seasons)
    for dataset, season in targets:
        url = DATASETS[dataset].format(season=season)
        body = fetch(url)
        rows = csv_rows(body, dataset)
        filename = f"{dataset}_{season}.csv" if season else f"{dataset}.csv"
        atomic_write(raw_dir / filename, body)
        requests.append({
            "dataset": dataset, "season": season, "url": url, "file": filename,
            "record_count": len(rows), "sha256": hashlib.sha256(body).hexdigest(),
            "columns": list(rows[0]),
        })
    manifest = {
        "schema_version": SCHEMA_VERSION, "source": "nflverse", "snapshot_id": snapshot_id,
        "fetched_at": fetched_at.isoformat(), "seasons": list(seasons),
        "identity_seasons": list(sorted(set(seasons) | set(identity_seasons))), "requests": requests,
        "license": "CC-BY-4.0; individual upstream datasets may have additional terms",
    }
    atomic_write(raw_dir / "manifest.json", (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())
    pointer = root / "data" / "raw" / "nflverse" / "latest.json"
    atomic_write(pointer, (json.dumps({"schema_version": 1, "snapshot_id": snapshot_id,
                                      "manifest": str((raw_dir / "manifest.json").relative_to(root))}, indent=2) + "\n").encode())
    return raw_dir


def load_snapshot(root: Path, snapshot_id: str | None) -> tuple[Path, dict[str, Any]]:
    if snapshot_id is None:
        pointer = json.loads((root / "data" / "raw" / "nflverse" / "latest.json").read_text())
        snapshot_id = pointer["snapshot_id"]
    raw_dir = root / "data" / "raw" / "nflverse" / snapshot_id
    manifest = json.loads((raw_dir / "manifest.json").read_text())
    return raw_dir, manifest


def normalize_sources(root: Path, raw_dir: Path, manifest: dict[str, Any], seasons: tuple[int, ...],
                      identity_seasons: tuple[int, ...] = ()) -> Path:
    snapshot_id = manifest["snapshot_id"]
    out_dir = root / "data" / "processed" / "nflverse" / snapshot_id
    players = csv_rows((raw_dir / "players.csv").read_bytes(), "players")
    player_fields = ["gsis_id", "display_name", "position", "position_group", "birth_date", "rookie_season",
                     "last_season", "latest_team", "status", "years_of_experience", "espn_id", "pfr_id", "pff_id"]
    write_csv(out_dir / "players.csv", players, player_fields)
    schedules = csv_rows((raw_dir / "schedules.csv").read_bytes(), "schedules")
    schedule_fields = ["season", "week", "game_type", "game_id", "home_team", "away_team", "home_score", "away_score"]
    selected_schedules = [row for row in schedules if int(row["season"]) in seasons]
    write_csv(out_dir / "schedules.csv", selected_schedules, schedule_fields)
    counts: dict[str, int] = {"players": len(players), "schedules": len(selected_schedules)}
    for season in seasons:
        stats = csv_rows((raw_dir / f"player_stats_{season}.csv").read_bytes(), "player_stats")
        stats = [row for row in stats if row["season_type"] == "REG" and int(row["season"]) == season]
        fields = ["player_id", "player_display_name", "position", "season", "week", "team", "opponent_team"] + list(PLAYER_STATS)
        write_csv(out_dir / f"player_stats_{season}.csv", stats, fields)
        rosters = csv_rows((raw_dir / f"rosters_{season}.csv").read_bytes(), "rosters")
        roster_fields = ["season", "week", "team", "full_name", "position", "status", "birth_date",
                         "years_exp", "gsis_id", "espn_id", "yahoo_id", "pfr_id", "pff_id", "sleeper_id"]
        write_csv(out_dir / f"rosters_{season}.csv", rosters, roster_fields)
        team_stats = csv_rows((raw_dir / f"team_stats_{season}.csv").read_bytes(), "team_stats")
        team_stats = [row for row in team_stats if row["season_type"] == "REG" and int(row["season"]) == season]
        team_fields = ["season", "week", "team", "opponent_team"] + list(TEAM_DEF_STATS)
        write_csv(out_dir / f"team_stats_{season}.csv", team_stats, team_fields)
        counts.update({f"player_stats_{season}": len(stats), f"rosters_{season}": len(rosters),
                       f"team_stats_{season}": len(team_stats)})
    for season in identity_seasons:
        if season in seasons:
            continue
        rosters = csv_rows((raw_dir / f"rosters_{season}.csv").read_bytes(), "rosters")
        roster_fields = ["season", "week", "team", "full_name", "position", "status", "birth_date",
                         "years_exp", "gsis_id", "espn_id", "yahoo_id", "pfr_id", "pff_id", "sleeper_id"]
        write_csv(out_dir / f"rosters_{season}.csv", rosters, roster_fields)
        counts[f"rosters_{season}"] = len(rosters)
    metadata = {"schema_version": SCHEMA_VERSION, "source": "nflverse", "snapshot_id": snapshot_id,
                "built_at": datetime.now(timezone.utc).isoformat(), "seasons": list(seasons),
                "identity_seasons": list(sorted(set(seasons) | set(identity_seasons))), "record_counts": counts,
                "raw_manifest": str((raw_dir / "manifest.json").relative_to(root))}
    atomic_write(out_dir / "manifest.json", (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode())
    latest = root / "data" / "processed" / "nflverse" / "latest.json"
    atomic_write(latest, (json.dumps({"schema_version": 1, "snapshot_id": snapshot_id,
                                     "manifest": str((out_dir / "manifest.json").relative_to(root))}, indent=2) + "\n").encode())
    return out_dir


def canonical_players(root: Path, season: int) -> list[dict[str, Any]]:
    pointer = json.loads((root / "data" / "processed" / "canonical_projections" / str(season) / "latest.json").read_text())
    return json.loads((root / pointer["artifact"]).read_text())["players"]


def build_crosswalk(root: Path, processed: Path, seasons: tuple[int, ...]) -> Path:
    master = list(csv.DictReader((processed / "players.csv").open(encoding="utf-8", newline="")))
    master_by_gsis = {row["gsis_id"]: row for row in master if row["gsis_id"]}
    master_by_name_pos: dict[tuple[str, str], dict[str, dict[str, str]]] = defaultdict(dict)
    for row in master:
        gsis = clean_id(row["gsis_id"])
        if gsis:
            master_by_name_pos[(normalize_name(row["display_name"]), normalize_position(row["position"]))][gsis] = row
    alias_payload = json.loads((root / "config" / "player_aliases.json").read_text())
    identity_aliases: dict[tuple[int, str, str], str] = {}
    for alias in alias_payload.get("aliases", []):
        if alias.get("source") != "identity":
            continue
        for season in alias.get("seasons", seasons):
            identity_aliases[(season, normalize_name(alias["source_name"]), normalize_position(alias["position"]))] = normalize_name(alias["registry_name"])
    output, exceptions = [], []
    methods: Counter[str] = Counter()
    for season in seasons:
        rosters = list(csv.DictReader((processed / f"rosters_{season}.csv").open(encoding="utf-8", newline="")))
        by_name_pos: dict[tuple[str, str], dict[str, dict[str, str]]] = defaultdict(dict)
        by_name_pos_team: dict[tuple[str, str, str | None], dict[str, dict[str, str]]] = defaultdict(dict)
        roster_by_gsis: dict[str, dict[str, str]] = {}
        for row in rosters:
            pos = normalize_position(row["position"])
            key = (normalize_name(row["full_name"]), pos)
            gsis = clean_id(row["gsis_id"])
            if gsis:
                roster_by_gsis[gsis] = row
                by_name_pos[key][gsis] = row
                by_name_pos_team[(*key, normalize_team(row["team"]))][gsis] = row
        for player in canonical_players(root, season):
            position = player["position"]
            existing_gsis = player.get("source_ids", {}).get("gsis")
            evidence_match, evidence_method, evidence_confidence = None, "unmatched", 0.0
            if position == "DEF":
                team = normalize_team(player.get("nfl_team"))
                evidence_match, evidence_method, evidence_confidence = {"gsis_id": f"team:{team}"}, "team_defense", 1.0
            else:
                key = (normalize_name(player["name"]), position)
                team_candidates = list(by_name_pos_team.get((*key, normalize_team(player.get("nfl_team"))), {}).values())
                name_candidates = list(by_name_pos.get(key, {}).values())
                if len(team_candidates) == 1:
                    evidence_match, evidence_method, evidence_confidence = team_candidates[0], "exact_name_position_team", 1.0
                elif len(name_candidates) == 1:
                    evidence_match, evidence_method, evidence_confidence = name_candidates[0], "exact_name_position", 0.9
                elif name_candidates:
                    evidence_method = "ambiguous"
                if evidence_match is None:
                    source_name = normalize_name(player["name"])
                    registry_name = identity_aliases.get((season, source_name, position), source_name)
                    master_candidates = list(master_by_name_pos.get((registry_name, position), {}).values())
                    if len(master_candidates) == 1:
                        evidence_match = master_candidates[0]
                        evidence_method = "reviewed_alias_master_registry" if registry_name != source_name else "exact_master_registry"
                        evidence_confidence = 1.0 if registry_name != source_name else 0.95
                    elif master_candidates:
                        evidence_method = "ambiguous_master_registry"
            if existing_gsis:
                if evidence_match and evidence_match["gsis_id"] != existing_gsis:
                    raise NflverseError(f"Identity evidence conflict for {season} {player['name']}: "
                                        f"stored {existing_gsis}, roster candidate {evidence_match['gsis_id']}")
                match, method, confidence = roster_by_gsis.get(existing_gsis, {"gsis_id": existing_gsis}), "direct_gsis", 1.0
            else:
                match, method, confidence = evidence_match, evidence_method, evidence_confidence
            methods[method] += 1
            if not match:
                exceptions.append({"season": season, "internal_player_id": player["internal_player_id"],
                                   "name": player["name"], "position": position, "reason": method})
                continue
            gsis = match["gsis_id"]
            ids = master_by_gsis.get(gsis, {}) | match
            output.append({
                "season": season, "internal_player_id": player["internal_player_id"],
                "fantasypros_id": player["source_ids"]["fantasypros"], "gsis_id": gsis,
                "yahoo_id": clean_id(ids.get("yahoo_id")), "espn_id": clean_id(ids.get("espn_id")),
                "pfr_id": clean_id(ids.get("pfr_id")), "pff_id": clean_id(ids.get("pff_id")),
                "name": player["name"], "position": position, "nfl_team": normalize_team(player.get("nfl_team")),
                "match_method": method, "match_confidence": confidence,
                "identity_origin_method": evidence_method if evidence_match else (player.get("identity_evidence") or {}).get("method", method),
                "identity_origin_confidence": evidence_confidence if evidence_match else (player.get("identity_evidence") or {}).get("confidence", confidence),
            })
    fp_keys: dict[tuple[int, int], str] = {}
    stable_keys: dict[tuple[int, str], int] = {}
    fp_across_seasons: dict[int, str] = {}
    gsis_across_seasons: dict[str, int] = {}
    source_id_transitions = []
    collisions = []
    for row in output:
        fp_key, stable_key = (row["season"], int(row["fantasypros_id"])), (row["season"], row["gsis_id"])
        if fp_key in fp_keys and fp_keys[fp_key] != row["gsis_id"]:
            collisions.append({"type": "fantasypros_to_multiple_gsis", "key": fp_key, "values": [fp_keys[fp_key], row["gsis_id"]]})
        if stable_key in stable_keys and stable_keys[stable_key] != int(row["fantasypros_id"]):
            collisions.append({"type": "gsis_to_multiple_fantasypros", "key": stable_key,
                               "values": [stable_keys[stable_key], row["fantasypros_id"]]})
        fp_id = int(row["fantasypros_id"])
        if fp_id in fp_across_seasons and fp_across_seasons[fp_id] != row["gsis_id"]:
            collisions.append({"type": "cross_season_fantasypros_identity_change", "key": fp_id,
                               "values": [fp_across_seasons[fp_id], row["gsis_id"]]})
        if row["gsis_id"] in gsis_across_seasons and gsis_across_seasons[row["gsis_id"]] != fp_id:
            transition = {"type": "fantasypros_id_changed_for_stable_gsis", "gsis_id": row["gsis_id"],
                          "fantasypros_ids": sorted({gsis_across_seasons[row["gsis_id"]], fp_id})}
            if transition not in source_id_transitions:
                source_id_transitions.append(transition)
        fp_keys[fp_key], stable_keys[stable_key] = row["gsis_id"], int(row["fantasypros_id"])
        fp_across_seasons[fp_id], gsis_across_seasons[row["gsis_id"]] = row["gsis_id"], fp_id
    if collisions:
        raise NflverseError(f"Identity registry has {len(collisions)} collisions; refusing publication")
    origin_methods = Counter(row["identity_origin_method"] for row in output)
    method_precision = {method: {"accepted": count, "validated_correct": None,
                                 "note": "Requires adjudicated gold labels"}
                        for method, count in sorted(origin_methods.items())}
    payload = {"metadata": {"schema_version": 1, "snapshot_id": processed.name, "seasons": list(seasons),
                            "record_count": len(output), "exception_count": len(exceptions),
                            "match_methods": dict(methods), "collision_count": 0,
                            "source_id_transition_count": len(source_id_transitions),
                            "source_id_transitions": source_id_transitions,
                            "identity_origin_methods": dict(origin_methods),
                            "method_precision": method_precision}, "players": output, "exceptions": exceptions}
    path = processed / "player_identity_crosswalk.json"
    atomic_write(path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())
    shadow = []
    for row in output:
        stable = f"nfl:def:{row['gsis_id'][5:]}" if row["gsis_id"].startswith("team:") else f"nfl:gsis:{row['gsis_id']}"
        shadow.append({"season": row["season"], "fantasypros_id": row["fantasypros_id"],
                       "old_internal_player_id": f"nfl:fantasypros:{row['fantasypros_id']}",
                       "stable_internal_player_id": stable, "match_method": row["match_method"]})
    atomic_write(processed / "identity_migration_shadow.json",
                 (json.dumps({"metadata": {"schema_version": 1, "record_count": len(shadow),
                                            "collision_count": 0}, "mappings": shadow}, indent=2, sort_keys=True) + "\n").encode())
    return path


def score_player(position: str, row: dict[str, str], league: dict[str, Any]) -> float:
    offense = league["scoring"]["offense"]
    if position == "K":
        kicking = league["scoring"]["kicking"]
        score = sum(number(row, field) * kicking[setting] for field, setting in (
            ("fg_made_0_19", "field_goal_made_0_19"), ("fg_made_20_29", "field_goal_made_20_29"),
            ("fg_made_30_39", "field_goal_made_30_39"), ("fg_made_40_49", "field_goal_made_40_49")))
        score += (number(row, "fg_made_50_59") + number(row, "fg_made_60_")) * kicking["field_goal_made_50_plus"]
        score += sum(number(row, field) * kicking[setting] for field, setting in (
            ("fg_missed_0_19", "field_goal_missed_0_19"), ("fg_missed_20_29", "field_goal_missed_20_29"),
            ("fg_missed_30_39", "field_goal_missed_30_39"), ("fg_missed_40_49", "field_goal_missed_40_49"),
            ("pat_made", "extra_point_made"), ("pat_missed", "extra_point_missed")))
        return round(score, 4)
    score = number(row, "passing_yards") / offense["passing_yards_per_point"]
    score += number(row, "passing_tds") * offense["passing_touchdown"]
    score += number(row, "passing_interceptions") * offense["interception"]
    score += number(row, "rushing_yards") / offense["rushing_yards_per_point"]
    score += number(row, "rushing_tds") * offense["rushing_touchdown"]
    score += number(row, "receiving_yards") / offense["receiving_yards_per_point"]
    score += number(row, "receiving_tds") * offense["receiving_touchdown"]
    score += number(row, "special_teams_tds") * offense["return_touchdown"]
    score += sum(number(row, key) for key in ("passing_2pt_conversions", "rushing_2pt_conversions", "receiving_2pt_conversions")) * offense["two_point_conversion"]
    score += number(row, "fumbles_lost_total") * offense["fumble_lost"]
    return round(score, 4)


def points_allowed_score(points: int, settings: dict[str, float]) -> float:
    key = ("points_allowed_0" if points == 0 else "points_allowed_1_6" if points <= 6 else
           "points_allowed_7_13" if points <= 13 else "points_allowed_14_20" if points <= 20 else
           "points_allowed_21_27" if points <= 27 else "points_allowed_28_34" if points <= 34 else "points_allowed_35_plus")
    return settings[key]


def score_defense(row: dict[str, str], points_allowed: int, league: dict[str, Any]) -> float:
    settings = league["scoring"]["defense_special_teams"]
    score = number(row, "def_sacks") * settings["sack"]
    score += number(row, "def_interceptions") * settings["interception"]
    score += number(row, "fumble_recovery_opp") * settings["fumble_recovery"]
    score += (number(row, "def_tds") * settings["touchdown"] +
              number(row, "special_teams_tds") * settings["kickoff_or_punt_return_touchdown"])
    score += number(row, "def_safeties") * settings["safety"]
    score += sum(number(row, key) for key in ("def_punt_blocks", "def_pat_blocks", "def_fg_blocks")) * settings["blocked_kick"]
    return round(score + points_allowed_score(points_allowed, settings), 4)


def build_actuals(root: Path, processed: Path, crosswalk_path: Path, seasons: tuple[int, ...]) -> Path:
    league = json.loads((root / "config" / "league.json").read_text())
    crosswalk = json.loads(crosswalk_path.read_text())["players"]
    ids = {(row["season"], row["gsis_id"]): row["internal_player_id"] for row in crosswalk}
    schedules = list(csv.DictReader((processed / "schedules.csv").open(encoding="utf-8", newline="")))
    allowed: dict[tuple[int, int, str], int] = {}
    for game in schedules:
        if game["game_type"] != "REG" or not game["home_score"] or not game["away_score"]:
            continue
        season, week = int(game["season"]), int(game["week"])
        allowed[(season, week, normalize_team(game["home_team"]))] = int(float(game["away_score"]))
        allowed[(season, week, normalize_team(game["away_team"]))] = int(float(game["home_score"]))
    weekly: list[dict[str, Any]] = []
    for season in seasons:
        rows = csv.DictReader((processed / f"player_stats_{season}.csv").open(encoding="utf-8", newline=""))
        for row in rows:
            position = normalize_position(row["position"])
            if position not in {"QB", "RB", "WR", "TE", "K"}:
                continue
            gsis = row["player_id"]
            weekly.append({"season": season, "week": int(row["week"]), "internal_player_id": ids.get((season, gsis)),
                           "gsis_id": gsis, "name": row["player_display_name"], "position": position,
                           "team": normalize_team(row["team"]), "league_points": score_player(position, row, league),
                           "scoring_status": "calculated"})
        team_rows = csv.DictReader((processed / f"team_stats_{season}.csv").open(encoding="utf-8", newline=""))
        for row in team_rows:
            week, team = int(row["week"]), normalize_team(row["team"])
            pa = allowed.get((season, week, team))
            if pa is None:
                continue
            weekly.append({"season": season, "week": week, "internal_player_id": ids.get((season, f"team:{team}")),
                           "gsis_id": f"team:{team}", "name": f"{team} Defense", "position": "DEF", "team": team,
                           "league_points": score_defense(row, pa, league), "points_allowed": pa,
                           "scoring_status": "calculated_schedule_points_allowed"})
    season_groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for row in weekly:
        season_groups[(row["season"], row["gsis_id"])].append(row)
    season_rows = []
    for (season, gsis), games in sorted(season_groups.items()):
        points = [game["league_points"] for game in games]
        base = games[0]
        season_rows.append({"season": season, "internal_player_id": base["internal_player_id"], "gsis_id": gsis,
                            "name": base["name"], "position": base["position"], "games": len(games),
                            "league_points": round(sum(points), 4), "points_per_game": round(sum(points) / len(points), 4)})
    payload = {"metadata": {"schema_version": 1, "source": "nflverse", "snapshot_id": processed.name,
                            "seasons": list(seasons), "weekly_record_count": len(weekly),
                            "season_record_count": len(season_rows), "scoring_config": "config/league.json"},
               "weekly": weekly, "seasons": season_rows}
    path = processed / "league_scored_actuals.json"
    atomic_write(path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())
    return path


def run(root: Path, seasons: tuple[int, ...], download: bool, snapshot_id: str | None,
        identity_seasons: tuple[int, ...] = ()) -> tuple[Path, Path, Path]:
    if download:
        raw_dir = acquire(root, seasons, identity_seasons)
        manifest = json.loads((raw_dir / "manifest.json").read_text())
    else:
        raw_dir, manifest = load_snapshot(root, snapshot_id)
        if not identity_seasons:
            identity_seasons = tuple(manifest.get("identity_seasons", seasons))
    processed = normalize_sources(root, raw_dir, manifest, seasons, identity_seasons)
    crosswalk = build_crosswalk(root, processed, tuple(sorted(set(seasons) | set(identity_seasons))))
    actuals = build_actuals(root, processed, crosswalk, seasons)
    return processed, crosswalk, actuals


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=int, nargs="+", default=DEFAULT_SEASONS)
    parser.add_argument("--identity-seasons", type=int, nargs="+", default=(),
                        help="Roster-only seasons used for identity matching without outcome data")
    parser.add_argument("--no-download", action="store_true", help="Rebuild from the latest preserved raw snapshot")
    parser.add_argument("--snapshot-id")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    seasons = tuple(sorted(set(args.seasons)))
    try:
        identity_seasons = tuple(sorted(set(args.identity_seasons)))
        processed, crosswalk, actuals = run(args.root.resolve(), seasons, not args.no_download, args.snapshot_id,
                                            identity_seasons)
        print(f"Wrote normalized nflverse data to {processed}")
        print(f"Wrote identity crosswalk to {crosswalk}")
        print(f"Wrote league-scored actuals to {actuals}")
    except (NflverseError, OSError, ValueError, KeyError, json.JSONDecodeError, csv.Error) as exc:
        print(f"nflverse pipeline failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
