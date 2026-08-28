#!/usr/bin/env python3
"""Fetch FantasyPros injuries, consensus rankings, and player news for offline use."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from .fantasypros_projections import PipelineError, atomic_write, load_dotenv
except ImportError:
    from fantasypros_projections import PipelineError, atomic_write, load_dotenv

API_BASE = "https://api.fantasypros.com/public/v2/json"
POSITIONS = ("QB", "RB", "WR", "TE", "K", "DST")
SCHEMA_VERSION = 1


def fetch(api_key: str, path: str, params: dict[str, Any]) -> tuple[bytes, dict[str, Any], str]:
    url = f"{API_BASE}{path}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={
        "x-api-key": api_key, "Accept": "application/json", "User-Agent": "jugg-league-analytics/1",
    })
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise PipelineError(f"FantasyPros returned HTTP {exc.code} for {path}: {exc.read(500).decode(errors='replace')}") from exc
    except urllib.error.URLError as exc:
        raise PipelineError(f"FantasyPros request failed for {path}: {exc.reason}") from exc
    try:
        return body, json.loads(body), url
    except json.JSONDecodeError as exc:
        raise PipelineError(f"FantasyPros returned non-JSON data for {path}") from exc


def clean_text(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = re.sub(r"<[^>]+>", " ", html.unescape(str(value)))
    return re.sub(r"\s+", " ", text).strip() or None


def validate_collection(payload: dict[str, Any], key: str, label: str) -> list[dict[str, Any]]:
    rows = payload.get(key)
    if not isinstance(rows, list):
        raise PipelineError(f"{label}: response has no {key} array")
    if int(payload.get("count", -1)) != len(rows):
        raise PipelineError(f"{label}: declared count does not match returned rows")
    return rows


def identity_map(root: Path, season: int) -> dict[int, str]:
    pointer = json.loads((root / "data" / "processed" / "canonical_projections" / str(season) / "latest.json").read_text())
    artifact = json.loads((root / pointer["artifact"]).read_text())
    return {int(row["source_ids"]["fantasypros"]): row["internal_player_id"] for row in artifact["players"]}


def normalize_rank(row: dict[str, Any], position: str, identities: dict[int, str]) -> dict[str, Any]:
    player_id = int(row["player_id"])
    return {
        "internal_player_id": identities.get(player_id), "fantasypros_id": player_id,
        "name": row.get("player_name"), "position": "DEF" if position == "DST" else position,
        "team": row.get("player_team_id"), "bye_week": row.get("player_bye_week"),
        "ecr": row.get("rank_ecr"), "position_rank": row.get("pos_rank"), "tier": row.get("tier"),
        "rank_average": row.get("rank_ave"), "rank_best": row.get("rank_min"),
        "rank_worst": row.get("rank_max"), "rank_stddev": row.get("rank_std"),
        "ecr_delta": row.get("player_ecr_delta"), "owned_average": row.get("player_owned_avg"),
        "owned_espn": row.get("player_owned_espn"), "owned_yahoo": row.get("player_owned_yahoo"),
    }


def normalize_injury(row: dict[str, Any], identities: dict[int, str]) -> dict[str, Any]:
    player_id = int(row["player_id"])
    return {
        "internal_player_id": identities.get(player_id), "fantasypros_id": player_id,
        "yahoo_id": row.get("yahoo_id"), "name": row.get("name"), "team": row.get("team_id"),
        "position": row.get("position_id"), "status": row.get("status") or None,
        "status_short": row.get("status_short") or None, "injury_type": row.get("injury_type") or None,
        "comment": clean_text(row.get("comment")), "injury_update_date": row.get("injury_update_date"),
        "ir_weeks": row.get("ir_weeks") or [], "probability_of_playing": row.get("probability_of_playing"),
        "practice_1": row.get("practice_1") or None, "practice_2": row.get("practice_2") or None,
        "practice_3": row.get("practice_3") or None,
        "practice_report_injury_type": row.get("practice_report_injury_type") or None,
    }


def normalize_news(row: dict[str, Any], identities: dict[int, str]) -> dict[str, Any]:
    raw_id = row.get("player_id")
    player_id = int(raw_id) if raw_id not in (None, "") else None
    return {
        "internal_player_id": identities.get(player_id) if player_id is not None else None,
        "fantasypros_id": player_id, "news_id": row.get("id"), "team": row.get("team_id"),
        "title": clean_text(row.get("title")), "description": clean_text(row.get("desc")),
        "impact": clean_text(row.get("impact")), "categories": row.get("categories") or [],
        "author": row.get("author"), "created_at": row.get("created"), "url": row.get("link"),
    }


def run(root: Path, season: int, week: int, news_limit: int, delay: float) -> tuple[Path, Path]:
    load_dotenv(root / ".env")
    api_key = os.environ.get("FANTASYPROS_API_KEY", "").strip()
    if not api_key:
        raise PipelineError("Set FANTASYPROS_API_KEY in the environment or project .env")
    retrieved = datetime.now(timezone.utc); snapshot_id = retrieved.strftime("%Y%m%dT%H%M%SZ")
    raw_dir = root / "data" / "raw" / "fantasypros_context" / str(season) / snapshot_id
    requests: list[dict[str, Any]] = []

    bodies: dict[str, tuple[bytes, dict[str, Any]]] = {}
    request_specs = [
        ("injuries", "/nfl/injuries", {"year": season, "week": week, "include_probabilities": "true"}),
        ("news", "/nfl/news", {"limit": news_limit, "order_by": "created"}),
    ] + [(f"rankings_{position.lower()}", f"/nfl/{season}/consensus-rankings",
          {"position": position, "scoring": "STD", "week": 0}) for position in POSITIONS]
    for index, (name, path, params) in enumerate(request_specs):
        if index and delay:
            time.sleep(delay)
        body, payload, url = fetch(api_key, path, params)
        collection = "injuries" if name == "injuries" else "items" if name == "news" else "players"
        rows = validate_collection(payload, collection, name)
        atomic_write(raw_dir / f"{name}.json", body)
        bodies[name] = body, payload
        requests.append({"dataset": name, "url": url, "file": f"{name}.json", "record_count": len(rows),
                         "sha256": hashlib.sha256(body).hexdigest(), "tier": payload.get("tier"),
                         "public_api_limited": payload.get("public_api_limited")})
    manifest = {"schema_version": SCHEMA_VERSION, "source": "fantasypros", "season": season, "week": week,
                "snapshot_id": snapshot_id, "retrieved_at": retrieved.isoformat(), "requests": requests}
    atomic_write(raw_dir / "manifest.json", (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode())

    identities = identity_map(root, season)
    injuries = [normalize_injury(row, identities) for row in validate_collection(bodies["injuries"][1], "injuries", "injuries")]
    news = [normalize_news(row, identities) for row in validate_collection(bodies["news"][1], "items", "news")]
    rankings = []
    for position in POSITIONS:
        rankings.extend(normalize_rank(row, position, identities) for row in
                        validate_collection(bodies[f"rankings_{position.lower()}"][1], "players", f"rankings_{position}"))

    by_player: dict[str, dict[str, Any]] = {}
    for row in rankings:
        if row["internal_player_id"]:
            by_player.setdefault(row["internal_player_id"], {"ranking": None, "injury": None, "recent_news": []})["ranking"] = row
    for row in injuries:
        if row["internal_player_id"]:
            by_player.setdefault(row["internal_player_id"], {"ranking": None, "injury": None, "recent_news": []})["injury"] = row
    for row in news:
        if row["internal_player_id"]:
            by_player.setdefault(row["internal_player_id"], {"ranking": None, "injury": None, "recent_news": []})["recent_news"].append(row)
    for context in by_player.values():
        context["recent_news"] = context["recent_news"][:5]

    out_dir = root / "data" / "processed" / "fantasypros_context" / str(season) / snapshot_id
    artifact = out_dir / "fantasypros_context.json"
    metadata = {**manifest, "ranking_count": len(rankings), "injury_count": len(injuries), "news_count": len(news),
                "player_context_count": len(by_player),
                "unmatched": {"rankings": sum(not row["internal_player_id"] for row in rankings),
                              "injuries": sum(not row["internal_player_id"] for row in injuries),
                              "news": sum(not row["internal_player_id"] for row in news)}}
    payload = {"metadata": metadata, "rankings": rankings, "injuries": injuries, "news": news,
               "ai_player_context": [{"internal_player_id": player_id, **context} for player_id, context in sorted(by_player.items())]}
    atomic_write(artifact, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())
    latest = root / "data" / "processed" / "fantasypros_context" / str(season) / "latest.json"
    atomic_write(latest, (json.dumps({"schema_version": 1, "snapshot_id": snapshot_id,
                                     "artifact": str(artifact.relative_to(root))}, indent=2) + "\n").encode())
    return raw_dir / "manifest.json", artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--week", type=int, default=1)
    parser.add_argument("--news-limit", type=int, default=100, choices=range(1, 101))
    parser.add_argument("--delay", type=float, default=0.25)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        raw, processed = run(args.root.resolve(), args.season, args.week, args.news_limit, args.delay)
        print(f"Wrote raw manifest {raw}"); print(f"Wrote normalized context {processed}")
    except (PipelineError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"FantasyPros context import failed: {exc}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
