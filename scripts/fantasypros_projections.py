#!/usr/bin/env python3
"""Fetch, preserve, normalize, and score FantasyPros NFL projections."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_BASE = "https://api.fantasypros.com/public/v2/json"
POSITIONS = ("QB", "RB", "WR", "TE", "K", "DST")
SCHEMA_VERSION = 1


class PipelineError(RuntimeError):
    """Raised when a safe, complete projection artifact cannot be produced."""


@dataclass(frozen=True)
class FetchResult:
    position: str
    body: bytes
    payload: dict[str, Any]
    url: str


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE entries without overriding the environment."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            os.environ.setdefault(key, value)


def as_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise PipelineError(f"Expected a numeric projection value, got {value!r}") from exc


def stat(stats: dict[str, Any], *names: str) -> float:
    for name in names:
        if name in stats and stats[name] not in (None, ""):
            return as_float(stats[name])
    return 0.0


def score_player(position: str, stats: dict[str, Any], league: dict[str, Any]) -> float:
    """Calculate projected points from counting stats and league rules."""
    scoring = league["scoring"]
    if position in {"QB", "RB", "WR", "TE"}:
        rules = scoring["offense"]
        points = (
            stat(stats, "pass_yds") / as_float(rules["passing_yards_per_point"])
            + stat(stats, "pass_tds") * as_float(rules["passing_touchdown"])
            + stat(stats, "pass_ints") * as_float(rules["interception"])
            + stat(stats, "rush_yds") / as_float(rules["rushing_yards_per_point"])
            + stat(stats, "rush_tds") * as_float(rules["rushing_touchdown"])
            + stat(stats, "rec_yds") / as_float(rules["receiving_yards_per_point"])
            + stat(stats, "rec_tds") * as_float(rules["receiving_touchdown"])
            + stat(stats, "ret_tds") * as_float(rules["return_touchdown"])
            + stat(stats, "2pt_tds", "two_pt_tds") * as_float(rules["two_point_conversion"])
            + stat(stats, "fumbles", "fumbles_lost") * as_float(rules["fumble_lost"])
        )
        return round(points, 3)

    if position == "K":
        rules = scoring["kicking"]
        # The current API supplies only aggregate made FGs and XPs. Credit each
        # FG at the league's minimum three points; unavailable 50+ bonuses and
        # miss penalties are intentionally not invented.
        points = (
            stat(stats, "fg") * min(
                as_float(rules["field_goal_made_0_19"]),
                as_float(rules["field_goal_made_20_29"]),
                as_float(rules["field_goal_made_30_39"]),
                as_float(rules["field_goal_made_40_49"]),
                as_float(rules["field_goal_made_50_plus"]),
            )
            + stat(stats, "fg_0_19", "fgm_0_19") * as_float(rules["field_goal_made_0_19"])
            + stat(stats, "fg_20_29", "fgm_20_29") * as_float(rules["field_goal_made_20_29"])
            + stat(stats, "fg_30_39", "fgm_30_39") * as_float(rules["field_goal_made_30_39"])
            + stat(stats, "fg_40_49", "fgm_40_49") * as_float(rules["field_goal_made_40_49"])
            + stat(stats, "fg_50", "fg_50_plus", "fgm_50_plus") * as_float(rules["field_goal_made_50_plus"])
            + stat(stats, "xpt", "xpm", "xp_made") * as_float(rules["extra_point_made"])
            + stat(stats, "xpt_miss", "xpmiss", "xp_missed") * as_float(rules["extra_point_missed"])
        )
        return round(points, 3)

    if position == "DEF":
        rules = scoring["defense_special_teams"]
        points = (
            stat(stats, "def_sack", "sacks") * as_float(rules["sack"])
            + stat(stats, "def_int", "interceptions") * as_float(rules["interception"])
            + stat(stats, "def_fr", "fumble_recoveries") * as_float(rules["fumble_recovery"])
            + stat(stats, "def_td", "touchdowns") * as_float(rules["touchdown"])
            + stat(stats, "def_safety", "safeties") * as_float(rules["safety"])
            + stat(stats, "def_block", "blocked_kicks") * as_float(rules["blocked_kick"])
            + stat(stats, "ret_tds", "def_retd") * as_float(rules["kickoff_or_punt_return_touchdown"])
            + stat(stats, "def_pa_a") * as_float(rules["points_allowed_0"])
            + stat(stats, "def_pa_b") * as_float(rules["points_allowed_1_6"])
            + stat(stats, "def_pa_c") * as_float(rules["points_allowed_7_13"])
            + stat(stats, "def_pa_d") * as_float(rules["points_allowed_14_20"])
            + stat(stats, "def_pa_e") * as_float(rules["points_allowed_21_27"])
            + stat(stats, "def_pa_f") * as_float(rules["points_allowed_28_34"])
            + stat(stats, "def_pa_g") * as_float(rules["points_allowed_35_plus"])
        )
        return round(points, 3)

    raise PipelineError(f"Unsupported normalized position: {position}")


def fetch_position(api_key: str, season: int, position: str, timeout: int = 30) -> FetchResult:
    query = urllib.parse.urlencode({"position": position, "week": 0})
    url = f"{API_BASE}/nfl/{season}/projections?{query}"
    request = urllib.request.Request(url, headers={
        "x-api-key": api_key,
        "Accept": "application/json",
        "User-Agent": "jugg-league-analytics/1",
    })
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read(500).decode("utf-8", errors="replace")
        raise PipelineError(f"FantasyPros returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise PipelineError(f"FantasyPros request failed: {exc.reason}") from exc
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise PipelineError("FantasyPros returned a non-JSON response") from exc
    validate_response(payload, season, position)
    return FetchResult(position=position, body=body, payload=payload, url=url)


def validate_response(payload: dict[str, Any], season: int, position: str) -> None:
    players = payload.get("players")
    if not isinstance(players, list):
        raise PipelineError(f"{position}: response has no players array")
    try:
        declared_count = int(payload["count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise PipelineError(f"{position}: response has no valid count") from exc
    if declared_count != len(players):
        raise PipelineError(f"{position}: incomplete response (declared {declared_count}, received {len(players)})")
    if str(payload.get("season")) != str(season) or str(payload.get("week")) != "0":
        raise PipelineError(f"{position}: response season/week does not match the request")
    if declared_count == 0:
        raise PipelineError(f"{position}: response contains no projections")


def normalize_player(player: dict[str, Any], requested_position: str, league: dict[str, Any]) -> dict[str, Any]:
    stats_value = player.get("stats", {})
    if isinstance(stats_value, list):
        if len(stats_value) != 1 or not isinstance(stats_value[0], dict):
            raise PipelineError(f"Unexpected stats structure for player {player.get('name')!r}")
        stats = stats_value[0]
    elif isinstance(stats_value, dict):
        stats = stats_value
    else:
        raise PipelineError(f"Missing stats for player {player.get('name')!r}")
    source_position = str(player.get("position_id") or requested_position).upper()
    position = "DEF" if source_position in {"DST", "DEF"} else source_position
    if position not in {"QB", "RB", "WR", "TE", "K", "DEF"}:
        raise PipelineError(f"Unexpected position {source_position!r}")
    fpid = player.get("fpid")
    name = player.get("name")
    if fpid in (None, "") or not name:
        raise PipelineError("Projection row is missing fpid or name")
    return {
        "fantasypros_id": int(fpid),
        "mfl_id": player.get("mflid"),
        "name": str(name),
        "position": position,
        "source_position": source_position,
        "nfl_team": player.get("team_id"),
        "stats": {key: value for key, value in sorted(stats.items())},
        "league_projected_points": score_player(position, stats, league),
        "league_scoring_status": "conservative_partial" if position == "K" else "calculated",
        "fantasypros_points_std": stats.get("points"),
        "fantasypros_points_half": stats.get("points_half"),
        "fantasypros_points_ppr": stats.get("points_ppr"),
    }


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_bytes(content)
    temp_path.replace(path)


def write_csv(path: Path, players: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    fields = ["fantasypros_id", "mfl_id", "name", "position", "source_position", "nfl_team",
              "league_projected_points", "league_scoring_status", "fantasypros_points_std", "fantasypros_points_half",
              "fantasypros_points_ppr", "stats_json"]
    with temp_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for player in players:
            row = {key: player.get(key) for key in fields if key != "stats_json"}
            row["stats_json"] = json.dumps(player["stats"], sort_keys=True, separators=(",", ":"))
            writer.writerow(row)
    temp_path.replace(path)


def run(season: int, root: Path, delay: float) -> tuple[Path, Path]:
    load_dotenv(root / ".env")
    api_key = os.environ.get("FANTASYPROS_API_KEY", "").strip()
    if not api_key:
        raise PipelineError("Set FANTASYPROS_API_KEY in the environment or project .env")
    league_path = root / "config" / "league.json"
    league = json.loads(league_path.read_text(encoding="utf-8"))
    retrieved_at = datetime.now(timezone.utc)
    snapshot_id = retrieved_at.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = root / "data" / "raw" / "fantasypros" / str(season) / snapshot_id
    results: list[FetchResult] = []
    for index, position in enumerate(POSITIONS):
        if index and delay:
            time.sleep(delay)
        results.append(fetch_position(api_key, season, position))

    manifest_requests = []
    players: list[dict[str, Any]] = []
    seen_ids: set[int] = set()
    for result in results:
        raw_path = raw_dir / f"{result.position.lower()}.json"
        atomic_write(raw_path, result.body)
        manifest_requests.append({
            "position": result.position,
            "url": result.url,
            "record_count": len(result.payload["players"]),
            "sha256": hashlib.sha256(result.body).hexdigest(),
            "file": raw_path.name,
            "tier": result.payload.get("tier"),
            "public_api_limited": result.payload.get("public_api_limited"),
        })
        for source_player in result.payload["players"]:
            normalized = normalize_player(source_player, result.position, league)
            player_id = normalized["fantasypros_id"]
            if player_id in seen_ids:
                raise PipelineError(f"Duplicate FantasyPros player ID across position responses: {player_id}")
            seen_ids.add(player_id)
            normalized.update({"season": season, "week": 0, "source": "fantasypros", "snapshot_id": snapshot_id})
            players.append(normalized)

    players.sort(key=lambda row: (row["position"], -row["league_projected_points"], row["name"]))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "source": "fantasypros",
        "season": season,
        "week": 0,
        "projection_type": "preseason_consensus",
        "retrieved_at": retrieved_at.isoformat(),
        "snapshot_id": snapshot_id,
        "league_config": str(league_path.relative_to(root)),
        "league_config_sha256": hashlib.sha256(league_path.read_bytes()).hexdigest(),
        "requests": manifest_requests,
        "total_players": len(players),
    }
    atomic_write(raw_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
    processed_dir = root / "data" / "processed" / "fantasypros" / str(season) / snapshot_id
    artifact = {"metadata": manifest, "players": players}
    json_path = processed_dir / "projections.json"
    csv_path = processed_dir / "projections.csv"
    atomic_write(json_path, json.dumps(artifact, indent=2, sort_keys=True).encode() + b"\n")
    write_csv(csv_path, players)
    latest_path = root / "data" / "processed" / "fantasypros" / str(season) / "latest.json"
    atomic_write(latest_path, json.dumps({
        "schema_version": 1,
        "snapshot_id": snapshot_id,
        "artifact": str(json_path.relative_to(root)),
    }, indent=2).encode() + b"\n")
    return json_path, csv_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=datetime.now().year)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--delay", type=float, default=1.05, help="Seconds between API requests")
    args = parser.parse_args()
    try:
        json_path, csv_path = run(args.season, args.root.resolve(), args.delay)
    except (PipelineError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"Projection import failed: {exc}", file=sys.stderr)
        return 1
    print(f"Wrote {json_path}")
    print(f"Wrote {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
