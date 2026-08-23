#!/usr/bin/env python3
"""Build FantasyPros-primary projections enriched with matched FFA rows."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
POSITIONS = {"QB", "RB", "WR", "TE", "K", "DEF"}
FFA_STAT_MAP = {
    "pass_yds": "pass_yds", "pass_tds": "pass_tds", "pass_int": "pass_ints",
    "rush_yds": "rush_yds", "rush_tds": "rush_tds", "fumbles_lost": "fumbles_lost",
    "two_pts": "2pt_tds", "return_tds": "ret_tds", "rec": "rec_rec",
    "rec_yds": "rec_yds", "rec_tds": "rec_tds", "fg_0019": "fg_0_19",
    "fg_2029": "fg_20_29", "fg_3039": "fg_30_39", "fg_4049": "fg_40_49",
    "fg_50": "fg_50_plus", "xp": "xpt", "dst_int": "def_int",
    "dst_sacks": "def_sack", "dst_safety": "def_safety", "dst_td": "def_td",
    "dst_blk": "def_block",
}
TEAM_ALIASES = {"JAC": "JAX", "LA": "LAR", "LVR": "LV", "OAK": "LV", "SD": "LAC", "STL": "LAR"}


class BuildError(RuntimeError):
    pass


def normalize_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    value = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", value.lower())
    return re.sub(r"[^a-z0-9]", "", value)


def normalize_position(value: str) -> str:
    value = (value or "").upper()
    return "DEF" if value in {"DST", "DEF"} else value


def normalize_team(value: str | None) -> str | None:
    if not value:
        return None
    value = value.upper()
    return TEAM_ALIASES.get(value, value)


def parse_value(value: str | None) -> Any:
    if value is None or value.strip() in {"", "NA", "N/A", "null"}:
        return None
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except ValueError:
        return value


def load_latest_fantasypros(root: Path, season: int) -> tuple[dict[str, Any], Path]:
    pointer_path = root / "data" / "processed" / "fantasypros" / str(season) / "latest.json"
    if not pointer_path.exists():
        raise BuildError(f"Missing FantasyPros latest pointer for {season}")
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    artifact_path = root / pointer["artifact"]
    return json.loads(artifact_path.read_text(encoding="utf-8")), artifact_path


def load_ffa(root: Path, season: int) -> tuple[list[dict[str, str]], Path]:
    path = root / "data" / "raw" / "ffa" / str(season) / f"raw_stats_{season}_wk0.csv"
    if not path.exists():
        raise BuildError(f"Missing FFA snapshot for {season}: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle)), path


def load_aliases(root: Path, season: int) -> dict[tuple[str, str], str]:
    path = root / "config" / "player_aliases.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    aliases: dict[tuple[str, str], str] = {}
    for entry in payload.get("aliases", []):
        if entry.get("source", "ffa") != "ffa":
            continue
        seasons = entry.get("seasons")
        if seasons and season not in seasons:
            continue
        position = normalize_position(entry["position"])
        source_name = entry.get("source_name", entry.get("ffa_name"))
        aliases[(normalize_name(source_name), position)] = normalize_name(entry["fantasypros_name"])
    return aliases


def index_ffa(rows: list[dict[str, str]], aliases: dict[tuple[str, str], str]) -> tuple[dict, dict, dict, int]:
    by_name_pos: dict[tuple[str, str], list[tuple[int, dict[str, str]]]] = {}
    by_name_pos_team: dict[tuple[str, str, str | None], list[tuple[int, dict[str, str]]]] = {}
    by_pos_team: dict[tuple[str, str | None], list[tuple[int, dict[str, str]]]] = {}
    seen_rows: set[tuple[tuple[str, str], ...]] = set()
    duplicate_count = 0
    for row_number, row in enumerate(rows, start=2):
        position = normalize_position(row.get("position", ""))
        if position not in POSITIONS:
            continue
        # FFA sometimes repeats the same source ID and identical projection
        # values while stale team or biographical metadata differs. Treat that
        # as one projection row; never collapse rows whose projected values or
        # uncertainty differ.
        projection_fields = sorted(
            {field for field in FFA_STAT_MAP for field in (field, field + "_sd")}
        )
        fingerprint = tuple(
            (field, row.get(field, ""))
            for field in ("id", "player", "position", "avg_type", *projection_fields)
        )
        if fingerprint in seen_rows:
            duplicate_count += 1
            continue
        seen_rows.add(fingerprint)
        source_name = normalize_name(row.get("player", ""))
        name = aliases.get((source_name, position), source_name)
        item = (row_number, row)
        by_name_pos.setdefault((name, position), []).append(item)
        by_name_pos_team.setdefault((name, position, normalize_team(row.get("team"))), []).append(item)
        by_pos_team.setdefault((position, normalize_team(row.get("team"))), []).append(item)
    return by_name_pos, by_name_pos_team, by_pos_team, duplicate_count


def match_ffa(player: dict[str, Any], by_name_pos: dict, by_name_pos_team: dict, by_pos_team: dict) -> tuple[Any, str]:
    key = (normalize_name(player["name"]), player["position"])
    team_key = (*key, normalize_team(player.get("nfl_team")))
    if player["position"] == "DEF":
        defense_candidates = by_pos_team.get(("DEF", normalize_team(player.get("nfl_team"))), [])
        if len(defense_candidates) == 1:
            return defense_candidates[0], "exact_position_team"
    team_candidates = by_name_pos_team.get(team_key, [])
    if len(team_candidates) == 1:
        return team_candidates[0], "exact_name_position_team"
    candidates = by_name_pos.get(key, [])
    if len(candidates) == 1:
        return candidates[0], "exact_name_position"
    if len(candidates) > 1:
        return candidates, "ambiguous_name_position"
    return None, "unmatched"


def ffa_enrichment(row: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    stats: dict[str, Any] = {}
    uncertainty: dict[str, Any] = {}
    for source_name, canonical_name in FFA_STAT_MAP.items():
        value = parse_value(row.get(source_name))
        if value is not None:
            stats[canonical_name] = value
        sd = parse_value(row.get(source_name + "_sd"))
        if sd is not None:
            uncertainty[canonical_name] = sd
    metadata = {key: parse_value(row.get(key)) for key in
                ("id", "avg_type", "draft_year", "birthdate", "injury_status", "injury_details")}
    return {key: value for key, value in metadata.items() if value is not None}, {
        "stats": stats, "stat_standard_deviations": uncertainty,
    }


def build_season(root: Path, season: int) -> Path:
    fantasypros, fp_path = load_latest_fantasypros(root, season)
    ffa_rows, ffa_path = load_ffa(root, season)
    aliases = load_aliases(root, season)
    by_name_pos, by_name_pos_team, by_pos_team, duplicate_ffa_rows = index_ffa(ffa_rows, aliases)
    built_at = datetime.now(timezone.utc)
    build_id = built_at.strftime("%Y%m%dT%H%M%SZ")
    output_players = []
    exceptions = []
    methods = Counter()

    for fp in fantasypros["players"]:
        match, method = match_ffa(fp, by_name_pos, by_name_pos_team, by_pos_team)
        methods[method] += 1
        stats = dict(fp["stats"])
        provenance = {f"stats.{key}": "fantasypros" for key in stats}
        canonical = {
            "internal_player_id": f"nfl:fantasypros:{fp['fantasypros_id']}",
            "season": season,
            "name": fp["name"], "position": fp["position"], "nfl_team": normalize_team(fp.get("nfl_team")),
            "source_ids": {"fantasypros": fp["fantasypros_id"]},
            "stats": stats,
            "field_provenance": provenance,
            "fantasypros": {
                "snapshot_id": fp["snapshot_id"],
                "league_projected_points": fp["league_projected_points"],
                "league_scoring_status": fp["league_scoring_status"],
                "points_std": fp.get("fantasypros_points_std"),
                "points_half": fp.get("fantasypros_points_half"),
                "points_ppr": fp.get("fantasypros_points_ppr"),
            },
            "enrichments": {},
            "match": {"ffa": {"method": method, "confidence": 1.0 if method.endswith("team") else 0.9 if method == "exact_name_position" else 0.0}},
        }
        if isinstance(match, tuple):
            row_number, row = match
            metadata, enrichment = ffa_enrichment(row)
            canonical["source_ids"]["ffa"] = parse_value(row.get("id"))
            canonical["enrichments"]["ffa"] = {"source_row": row_number, "metadata": metadata, **enrichment}
            canonical["match"]["ffa"]["source_row"] = row_number
            canonical["match"]["ffa"]["source_name"] = row.get("player")
            # FantasyPros remains authoritative. FFA only fills stats absent
            # from the primary source, with explicit field provenance.
            for field, value in enrichment["stats"].items():
                if field not in stats:
                    stats[field] = value
                    provenance[f"stats.{field}"] = "ffa"
        else:
            exceptions.append({
                "fantasypros_id": fp["fantasypros_id"], "name": fp["name"], "position": fp["position"],
                "team": fp.get("nfl_team"), "reason": method,
                "ffa_candidates": [x[1].get("player") for x in match] if isinstance(match, list) else [],
            })
        output_players.append(canonical)

    metadata = {
        "schema_version": SCHEMA_VERSION, "season": season, "build_id": build_id,
        "built_at": built_at.isoformat(), "primary_source": "fantasypros",
        "enrichment_sources": ["ffa"],
        "inputs": {
            "fantasypros": {"path": str(fp_path.relative_to(root)), "sha256": hashlib.sha256(fp_path.read_bytes()).hexdigest()},
            "ffa": {"path": str(ffa_path.relative_to(root)), "sha256": hashlib.sha256(ffa_path.read_bytes()).hexdigest()},
        },
        "player_count": len(output_players), "match_methods": dict(methods),
        "matched_ffa_count": sum(value for key, value in methods.items() if key.startswith("exact_")),
        "exception_count": len(exceptions), "deduplicated_ffa_source_rows": duplicate_ffa_rows,
    }
    out_dir = root / "data" / "processed" / "canonical_projections" / str(season) / build_id
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = out_dir / "projections.json"
    artifact_path.write_text(json.dumps({"metadata": metadata, "players": output_players}, indent=2, sort_keys=True) + "\n")
    (out_dir / "match_exceptions.json").write_text(json.dumps({"metadata": metadata, "exceptions": exceptions}, indent=2, sort_keys=True) + "\n")
    latest = root / "data" / "processed" / "canonical_projections" / str(season) / "latest.json"
    latest.write_text(json.dumps({"schema_version": 1, "build_id": build_id, "artifact": str(artifact_path.relative_to(root))}, indent=2) + "\n")
    return artifact_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=int, nargs="+", default=list(range(2020, 2027)))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        for season in args.seasons:
            print(f"Wrote {build_season(args.root.resolve(), season)}")
    except (BuildError, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"Canonical build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
