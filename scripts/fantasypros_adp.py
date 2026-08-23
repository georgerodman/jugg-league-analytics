#!/usr/bin/env python3
"""Fetch FantasyPros historical Yahoo and ESPN NFL ADP snapshots."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.fantasypros_projections import PipelineError, atomic_write, load_dotenv
except ModuleNotFoundError:  # Direct execution places scripts/ on sys.path.
    from fantasypros_projections import PipelineError, atomic_write, load_dotenv

API_BASE = "https://api.fantasypros.com/public/v2/json"
SOURCES = {
    "yahoo": {"scoring": "HALF", "expert_id": "236"},
    "espn": {"scoring": "PPR", "expert_id": "79"},
}


def fetch(api_key: str, season: int, scoring: str) -> tuple[bytes, dict[str, Any], str]:
    query = urllib.parse.urlencode({
        "position": "ALL", "type": "ADP", "scoring": scoring, "week": 0, "experts": "show",
    })
    url = f"{API_BASE}/nfl/{season}/consensus-rankings?{query}"
    request = urllib.request.Request(url, headers={
        "x-api-key": api_key, "Accept": "application/json", "User-Agent": "jugg-league-analytics/1",
    })
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read(300).decode("utf-8", errors="replace")
        raise PipelineError(f"{season} {scoring} ADP returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise PipelineError(f"{season} {scoring} ADP request failed: {exc.reason}") from exc
    payload = json.loads(body)
    players = payload.get("players")
    if not isinstance(players, list) or not players:
        raise PipelineError(f"{season} {scoring}: response contains no ADP players")
    if int(payload.get("count", -1)) != len(players):
        raise PipelineError(f"{season} {scoring}: declared and received ADP counts differ")
    if str(payload.get("year")) != str(season) or payload.get("scoring") != scoring:
        raise PipelineError(f"{season} {scoring}: response metadata does not match request")
    return body, payload, url


def extract_source(payload: dict[str, Any], platform: str) -> dict[int, dict[str, Any]]:
    expert_id = SOURCES[platform]["expert_id"]
    output = {}
    for player in payload["players"]:
        value = player.get("experts", {}).get(expert_id)
        if value in (None, "", "-", "N/A"):
            continue
        try:
            adp = float(value)
        except (TypeError, ValueError) as exc:
            raise PipelineError(f"Invalid {platform} ADP value {value!r}") from exc
        player_id = int(player["player_id"])
        output[player_id] = {
            "fantasypros_id": player_id,
            "name": player.get("player_name"),
            "position": "DEF" if player.get("player_position_id") in {"DST", "DEF"} else player.get("player_position_id"),
            "nfl_team": player.get("player_team_id"),
            f"adp_{platform}": adp,
        }
    if not output:
        raise PipelineError(f"No {platform} rows found using FantasyPros source ID {expert_id}")
    return output


def run(root: Path, season: int, delay: float) -> Path:
    load_dotenv(root / ".env")
    api_key = os.environ.get("FANTASYPROS_API_KEY", "").strip()
    if not api_key:
        raise PipelineError("Set FANTASYPROS_API_KEY in the environment or project .env")
    retrieved_at = datetime.now(timezone.utc)
    snapshot_id = retrieved_at.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = root / "data" / "raw" / "fantasypros_adp" / str(season) / snapshot_id
    responses = {}
    for index, scoring in enumerate(("HALF", "PPR")):
        if index and delay:
            time.sleep(delay)
        responses[scoring] = fetch(api_key, season, scoring)

    requests = []
    for scoring, (body, payload, url) in responses.items():
        filename = f"{scoring.lower()}.json"
        atomic_write(raw_dir / filename, body)
        requests.append({
            "scoring": scoring, "url": url, "file": filename, "record_count": len(payload["players"]),
            "sha256": hashlib.sha256(body).hexdigest(), "tier": payload.get("tier"),
            "public_api_limited": payload.get("public_api_limited"), "available_source_ids": payload.get("filters"),
            "last_updated": payload.get("last_updated"), "last_updated_ts": payload.get("last_updated_ts"),
        })

    yahoo = extract_source(responses["HALF"][1], "yahoo")
    espn = extract_source(responses["PPR"][1], "espn")
    combined = {}
    for rows in (yahoo, espn):
        for player_id, row in rows.items():
            combined.setdefault(player_id, {
                "fantasypros_id": player_id, "name": row["name"], "position": row["position"],
                "nfl_team": row["nfl_team"], "adp_yahoo": None, "adp_espn": None,
            }).update({key: value for key, value in row.items() if key.startswith("adp_")})
    players = sorted(combined.values(), key=lambda row: (min(value for value in (row["adp_yahoo"], row["adp_espn"]) if value is not None), row["name"] or ""))
    manifest = {
        "schema_version": 1, "source": "fantasypros", "dataset": "platform_adp", "season": season,
        "week": 0, "snapshot_id": snapshot_id, "retrieved_at": retrieved_at.isoformat(),
        "platforms": {
            "yahoo": {"fantasypros_expert_id": 236, "scoring_pool": "HALF", "player_count": len(yahoo)},
            "espn": {"fantasypros_expert_id": 79, "scoring_pool": "PPR", "player_count": len(espn)},
        },
        "requests": requests, "combined_player_count": len(players),
    }
    atomic_write(raw_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
    out_dir = root / "data" / "processed" / "fantasypros_adp" / str(season) / snapshot_id
    artifact = out_dir / "adp.json"
    atomic_write(artifact, json.dumps({"metadata": manifest, "players": players}, indent=2, sort_keys=True).encode() + b"\n")
    latest = root / "data" / "processed" / "fantasypros_adp" / str(season) / "latest.json"
    atomic_write(latest, json.dumps({"schema_version": 1, "snapshot_id": snapshot_id, "artifact": str(artifact.relative_to(root))}, indent=2).encode() + b"\n")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=int, nargs="+", default=list(range(2020, 2027)))
    parser.add_argument("--delay", type=float, default=1.1)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        for season in args.seasons:
            print(f"Wrote {run(args.root.resolve(), season, args.delay)}")
    except (PipelineError, OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"ADP import failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
