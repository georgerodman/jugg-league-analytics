#!/usr/bin/env python3
"""Match historical auction sales to canonical FantasyPros-backed identities."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_canonical_projections import normalize_name, normalize_position, normalize_team


def load_canonical(root: Path, season: int) -> dict[str, Any]:
    pointer = json.loads((root / "data" / "processed" / "canonical_projections" / str(season) / "latest.json").read_text())
    return json.loads((root / pointer["artifact"]).read_text())


def run(root: Path) -> Path:
    with (root / "data" / "raw" / "auction_history.csv").open(encoding="utf-8-sig", newline="") as handle:
        sales = list(csv.DictReader(handle))
    alias_payload = json.loads((root / "config" / "player_aliases.json").read_text())
    owner_alias_payload = json.loads((root / "config" / "owner_aliases.json").read_text())
    owner_aliases = {
        (int(entry["season"]), entry["source_team"].strip().casefold()): entry["owner"]
        for entry in owner_alias_payload.get("aliases", [])
    }
    aliases = {}
    for entry in alias_payload.get("aliases", []):
        if entry.get("source") != "auction_history":
            continue
        for season in entry.get("seasons", []):
            aliases[(season, normalize_name(entry["source_name"]), normalize_position(entry["position"]))] = normalize_name(entry["fantasypros_name"])
    indexes = {}
    global_by_name_pos = {}
    canonical_seasons = sorted(
        int(path.parent.name)
        for path in (root / "data" / "processed" / "canonical_projections").glob("*/latest.json")
        if path.parent.name.isdigit()
    )
    for season in canonical_seasons:
        canonical = load_canonical(root, season)
        by_name_pos = {}
        by_name_pos_team = {}
        for player in canonical["players"]:
            key = (normalize_name(player["name"]), player["position"])
            by_name_pos.setdefault(key, []).append(player)
            by_name_pos_team.setdefault((*key, normalize_team(player.get("nfl_team"))), []).append(player)
            global_by_name_pos.setdefault(key, {})[player["internal_player_id"]] = player
        indexes[season] = (by_name_pos, by_name_pos_team)

    output = []
    methods = Counter()
    for source_row, sale in enumerate(sales, start=2):
        season = int(sale["Season"])
        position = normalize_position(sale["Pos"])
        source_name = normalize_name(sale["Player"])
        key = (aliases.get((season, source_name, position), source_name), position)
        by_name_pos, by_name_pos_team = indexes.get(season, ({}, {}))
        team_candidates = by_name_pos_team.get((*key, normalize_team(sale.get("Team"))), [])
        name_candidates = by_name_pos.get(key, [])
        if len(team_candidates) == 1:
            match, method, confidence = team_candidates[0], "exact_name_position_team", 1.0
        elif len(name_candidates) == 1:
            match, method, confidence = name_candidates[0], "exact_name_position", 0.9
        elif len(global_by_name_pos.get(key, {})) == 1:
            match = next(iter(global_by_name_pos[key].values()))
            method, confidence = "global_exact_name_position", 0.8
        elif len(name_candidates) > 1:
            match, method, confidence = None, "ambiguous_name_position", 0.0
        else:
            match, method, confidence = None, "unmatched", 0.0
        if match is None and season < min(canonical_seasons):
            digest = hashlib.sha256(f"{season}|{key[0]}|{position}".encode()).hexdigest()[:16]
            provisional_id = f"auction_history:yahoo:{digest}"
            method, confidence = "legacy_provisional", 0.0
        else:
            provisional_id = None
        methods[method] += 1
        output.append({
            "source_row": source_row, "season": season,
            "owner": owner_aliases.get((season, sale["FF Team"].strip().casefold()), sale["FF Team"]),
            "source_team": sale["FF Team"],
            "player_name": sale["Player"], "position": position, "nfl_team": normalize_team(sale.get("Team")),
            "salary": int(sale["Salary"].replace("$", "")), "match_method": method,
            "match_confidence": confidence,
            "internal_player_id": match["internal_player_id"] if match else provisional_id,
            "fantasypros_id": match["source_ids"]["fantasypros"] if match else None,
            "candidates": [candidate["internal_player_id"] for candidate in name_candidates] if not match else [],
        })
    built_at = datetime.now(timezone.utc)
    build_id = built_at.strftime("%Y%m%dT%H%M%SZ")
    payload = {"metadata": {
        "schema_version": 1, "build_id": build_id, "built_at": built_at.isoformat(),
        "source": "data/raw/auction_history.csv", "sale_count": len(output),
        "match_methods": dict(methods),
        "matched_count": sum(v for k, v in methods.items() if k.startswith("exact_") or k.startswith("global_exact_")),
    }, "sales": output}
    out_dir = root / "data" / "processed" / "auction_history_matches" / build_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "auction_history_matches.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    latest = root / "data" / "processed" / "auction_history_matches" / "latest.json"
    latest.write_text(json.dumps({"schema_version": 1, "build_id": build_id, "artifact": str(path.relative_to(root))}, indent=2) + "\n")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(f"Wrote {run(args.root.resolve())}")
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"Auction matching failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
