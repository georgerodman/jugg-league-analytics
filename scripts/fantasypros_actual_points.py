#!/usr/bin/env python3
"""Fetch and preserve historical FantasyPros standard-scoring player points."""

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

from fantasypros_projections import PipelineError, atomic_write, load_dotenv

API_BASE = "https://api.fantasypros.com/public/v2/json"
POSITIONS = ("QB", "RB", "WR", "TE")


def fetch(api_key: str, season: int, position: str) -> tuple[bytes, dict[str, Any], str]:
    end_week = 17 if season == 2020 else 18
    query = urllib.parse.urlencode({"position": position, "start": 1, "end": end_week})
    url = f"{API_BASE}/nfl/{season}/player-points?{query}"
    request = urllib.request.Request(url, headers={
        "x-api-key": api_key, "Accept": "application/json", "User-Agent": "jugg-league-analytics/1",
    })
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise PipelineError(f"{season} {position}: FantasyPros returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise PipelineError(f"{season} {position}: request failed: {exc.reason}") from exc
    payload = json.loads(body)
    players = payload.get("players")
    if not isinstance(players, list) or not players:
        raise PipelineError(f"{season} {position}: response contains no players")
    if str(payload.get("season")) != str(season) or payload.get("scoring") != "STD":
        raise PipelineError(f"{season} {position}: unexpected season or scoring type")
    if any(player.get("player_id") is None for player in players):
        raise PipelineError(f"{season} {position}: player row is missing an ID")
    return body, payload, url


def normalize_position(value: Any) -> str:
    value = str(value or "").upper()
    return "DEF" if value in {"DST", "DEF"} else value


def run(root: Path, season: int, delay: float) -> Path:
    load_dotenv(root / ".env")
    api_key = os.environ.get("FANTASYPROS_API_KEY", "").strip()
    if not api_key:
        raise PipelineError("Set FANTASYPROS_API_KEY in the environment or project .env")
    fetched_at = datetime.now(timezone.utc)
    snapshot_id = fetched_at.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = root / "data" / "raw" / "fantasypros_actuals" / str(season) / snapshot_id
    results = []
    for index, position in enumerate(POSITIONS):
        if index and delay:
            time.sleep(delay)
        results.append((position, *fetch(api_key, season, position)))

    manifest_requests = []
    players = []
    seen = set()
    for position, body, payload, url in results:
        path = raw_dir / f"{position.lower()}.json"
        atomic_write(path, body)
        manifest_requests.append({
            "position": position, "url": url, "record_count": len(payload["players"]),
            "sha256": hashlib.sha256(body).hexdigest(), "file": path.name,
            "tier": payload.get("tier"), "public_api_limited": payload.get("public_api_limited"),
        })
        # Historical endpoints occasionally include a multi-position player
        # under a neighboring position request. Keep only the requested
        # position so cross-request duplicates cannot enter the artifact.
        for row in payload["players"]:
            if normalize_position(row.get("position_id")) != position:
                continue
            player_id = int(row["player_id"])
            if player_id in seen:
                raise PipelineError(f"Duplicate actual-points player ID {player_id}")
            seen.add(player_id)
            players.append({
                "fantasypros_id": player_id, "name": row["player_name"], "position": position,
                "nfl_team": row.get("team_id"), "games": row.get("games"),
                "points_std": row.get("points"), "average_std": row.get("average"),
            })
    manifest = {
        "schema_version": 1, "source": "fantasypros", "dataset": "actual_player_points_std",
        "season": season, "snapshot_id": snapshot_id, "fetched_at": fetched_at.isoformat(),
        "requests": manifest_requests, "player_count": len(players),
    }
    atomic_write(raw_dir / "manifest.json", json.dumps(manifest, indent=2, sort_keys=True).encode() + b"\n")
    out_dir = root / "data" / "processed" / "fantasypros_actuals" / str(season) / snapshot_id
    artifact = out_dir / "player_points.json"
    atomic_write(artifact, json.dumps({"metadata": manifest, "players": players}, indent=2, sort_keys=True).encode() + b"\n")
    latest = root / "data" / "processed" / "fantasypros_actuals" / str(season) / "latest.json"
    atomic_write(latest, json.dumps({"schema_version": 1, "snapshot_id": snapshot_id, "artifact": str(artifact.relative_to(root))}, indent=2).encode() + b"\n")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=int, nargs="+", default=list(range(2020, 2026)))
    parser.add_argument("--delay", type=float, default=1.05)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        for season in args.seasons:
            print(f"Wrote {run(args.root.resolve(), season, args.delay)}")
    except (PipelineError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"Actual-points import failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
