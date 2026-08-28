#!/usr/bin/env python3
"""Acquire nflverse weekly depth charts and publish the latest local team view."""

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
from typing import Any

try:
    from .build_canonical_projections import normalize_team
    from .fantasypros_projections import atomic_write
except ImportError:
    from build_canonical_projections import normalize_team
    from fantasypros_projections import atomic_write


SCHEMA_VERSION = 1
URL = "https://github.com/nflverse/nflverse-data/releases/download/depth_charts/depth_charts_{season}.csv"
REQUIRED_COLUMNS = {
    "dt", "team", "player_name", "espn_id", "gsis_id", "pos_grp_id", "pos_grp",
    "pos_id", "pos_name", "pos_abb", "pos_slot", "pos_rank",
}
FANTASY_GROUPS = {
    "QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "LWR": "WR", "RWR": "WR",
    "SWR": "WR", "TE": "TE", "LT": "OL", "LG": "OL", "C": "OL", "RG": "OL",
    "RT": "OL", "K": "K", "PK": "K", "P": "P",
}


class DepthChartError(RuntimeError):
    pass


def fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"Accept": "text/csv", "User-Agent": "jugg-league-analytics/1"})
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        raise DepthChartError(f"Failed to download {url}: {exc}") from exc
    if not body or b"," not in body[:4096]:
        raise DepthChartError(f"Downloaded data is empty or not CSV: {url}")
    return body


def parse_rows(body: bytes) -> tuple[list[dict[str, str]], list[str]]:
    reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    fields = reader.fieldnames or []
    missing = REQUIRED_COLUMNS - set(fields)
    if missing:
        raise DepthChartError(f"Depth-chart schema is missing columns: {sorted(missing)}")
    rows = list(reader)
    if not rows:
        raise DepthChartError("Depth-chart file contains no records")
    return rows, fields


def integer(value: str | None) -> int | None:
    if value in {None, "", "NA", "N/A", "null"}:
        return None
    return int(float(value))


def fantasy_group(row: dict[str, str]) -> str | None:
    abbreviation = row.get("pos_abb", "").upper()
    if abbreviation in FANTASY_GROUPS:
        return FANTASY_GROUPS[abbreviation]
    name = row.get("pos_name", "").lower()
    for phrase, group in (("quarterback", "QB"), ("running back", "RB"), ("fullback", "RB"),
                          ("wide receiver", "WR"), ("tight end", "TE")):
        if phrase in name:
            return group
    return None


def normalize_latest(rows: list[dict[str, str]], season: int, retrieved_at: str) -> dict[str, Any]:
    timestamps = sorted({row["dt"] for row in rows if row.get("dt")})
    if not timestamps:
        raise DepthChartError("Depth-chart records have no snapshot timestamps")
    latest_timestamp = timestamps[-1]
    latest = [row for row in rows if row["dt"] == latest_timestamp]
    if len({row["team"] for row in latest}) != 32:
        raise DepthChartError(f"Latest snapshot has {len({row['team'] for row in latest})} teams instead of 32")
    seen: set[tuple[str, str, str, int | None]] = set()
    players: list[dict[str, Any]] = []
    for row in latest:
        gsis_id = row.get("gsis_id") or None
        espn_id = row.get("espn_id") or None
        rank = integer(row.get("pos_rank"))
        team = normalize_team(row["team"]) or row["team"]
        key = (team, gsis_id or espn_id or row["player_name"], row["pos_abb"], rank)
        if key in seen:
            continue
        seen.add(key)
        internal_id = f"nfl:gsis:{gsis_id}" if gsis_id else (f"provisional:nflverse-depth:espn:{espn_id}" if espn_id else None)
        players.append({
            "internal_player_id": internal_id,
            "gsis_id": gsis_id,
            "espn_id": espn_id,
            "name": row["player_name"] or None,
            "team": team,
            "source_team": row["team"],
            "position_group": row["pos_grp"],
            "position_name": row["pos_name"],
            "position_abbreviation": row["pos_abb"],
            "position_slot": integer(row.get("pos_slot")),
            "depth_rank": rank,
            "fantasy_group": fantasy_group(row),
        })
    players.sort(key=lambda row: (row["team"], row["position_group"], row["position_slot"] or 999,
                                  row["depth_rank"] or 999, row["name"]))
    by_team: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in players:
        by_team[row["team"]].append(row)
    teams = []
    for team in sorted(by_team):
        roster = by_team[team]
        fantasy_offense = {
            group: sorted((row for row in roster if row["fantasy_group"] == group and row["name"]),
                          key=lambda row: (row["depth_rank"] or 999, row["position_slot"] or 999, row["name"]))
            for group in ("QB", "RB", "WR", "TE")
        }
        teams.append({"team": team, "fantasy_offense": fantasy_offense, "depth_chart": roster})
    counts = Counter(row["fantasy_group"] or "other" for row in players)
    return {
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "source": "nflverse depth charts (ESPN-derived for 2025+)",
            "season": season,
            "snapshot_at": latest_timestamp,
            "retrieved_at": retrieved_at,
            "available_snapshot_count": len(timestamps),
            "team_count": len(teams),
            "record_count": len(players),
            "unnamed_record_count": sum(not row["name"] for row in players),
            "gsis_identity_count": sum(bool(row["gsis_id"]) for row in players),
            "provisional_identity_count": sum(not row["gsis_id"] for row in players),
            "fantasy_group_counts": dict(sorted(counts.items())),
            "license": "CC-BY-SA-4.0 for 2025+ depth charts; credit ESPN via nflverse",
        },
        "teams": teams,
        "players": players,
    }


def run(root: Path, season: int, download: bool = True) -> tuple[Path, Path]:
    raw_base = root / "data" / "raw" / "nflverse_depth_charts" / str(season)
    if download:
        retrieved = datetime.now(timezone.utc)
        snapshot_id = retrieved.strftime("%Y%m%dT%H%M%SZ")
        url = URL.format(season=season)
        body = fetch(url)
        rows, fields = parse_rows(body)
        raw_dir = raw_base / snapshot_id
        raw_file = raw_dir / f"depth_charts_{season}.csv"
        atomic_write(raw_file, body)
        raw_manifest = {
            "schema_version": SCHEMA_VERSION, "source": "nflverse", "dataset": "depth_charts",
            "season": season, "snapshot_id": snapshot_id, "retrieved_at": retrieved.isoformat(),
            "url": url, "file": raw_file.name, "record_count": len(rows), "columns": fields,
            "sha256": hashlib.sha256(body).hexdigest(),
            "license": "CC-BY-SA-4.0 for 2025+ depth charts; credit ESPN via nflverse",
        }
        atomic_write(raw_dir / "manifest.json", (json.dumps(raw_manifest, indent=2, sort_keys=True) + "\n").encode())
        atomic_write(raw_base / "latest.json", (json.dumps({"schema_version": SCHEMA_VERSION,
                     "snapshot_id": snapshot_id, "manifest": str((raw_dir / "manifest.json").relative_to(root))}, indent=2) + "\n").encode())
    else:
        pointer_path = raw_base / "latest.json"
        if pointer_path.exists():
            pointer = json.loads(pointer_path.read_text())
            raw_dir = root / pointer["manifest"]
            raw_dir = raw_dir.parent
        else:
            candidates = sorted(path for path in raw_base.iterdir() if path.is_dir() and (path / "manifest.json").exists())
            if not candidates:
                raise DepthChartError(f"No preserved raw depth-chart snapshot for {season}")
            raw_dir = candidates[-1]
        raw_manifest = json.loads((raw_dir / "manifest.json").read_text())
        snapshot_id = raw_manifest["snapshot_id"]
        body = (raw_dir / raw_manifest["file"]).read_bytes()
        rows, fields = parse_rows(body)
        if hashlib.sha256(body).hexdigest() != raw_manifest["sha256"]:
            raise DepthChartError("Preserved raw depth-chart checksum does not match its manifest")
        retrieved = datetime.fromisoformat(raw_manifest["retrieved_at"])
        atomic_write(raw_base / "latest.json", (json.dumps({"schema_version": SCHEMA_VERSION,
                     "snapshot_id": snapshot_id, "manifest": str((raw_dir / "manifest.json").relative_to(root))}, indent=2) + "\n").encode())
    artifact = normalize_latest(rows, season, retrieved.isoformat())
    artifact["metadata"]["raw_manifest"] = str((raw_dir / "manifest.json").relative_to(root))
    processed_dir = root / "data" / "processed" / "nflverse_depth_charts" / str(season) / snapshot_id
    artifact_path = processed_dir / "depth_charts.json"
    atomic_write(artifact_path, (json.dumps(artifact, indent=2, sort_keys=True) + "\n").encode())
    pointer = {"schema_version": SCHEMA_VERSION, "season": season, "snapshot_id": snapshot_id,
               "artifact": str(artifact_path.relative_to(root))}
    atomic_write(root / "data" / "processed" / "nflverse_depth_charts" / str(season) / "latest.json",
                 (json.dumps(pointer, indent=2) + "\n").encode())
    return raw_dir / "manifest.json", artifact_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument("--no-download", action="store_true", help="Rebuild from the latest preserved raw snapshot")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        raw, artifact = run(args.root.resolve(), args.season, not args.no_download)
        print(f"Wrote raw manifest {raw}")
        print(f"Wrote normalized depth charts {artifact}")
    except (DepthChartError, OSError, ValueError, KeyError, json.JSONDecodeError, csv.Error) as exc:
        print(f"nflverse depth-chart import failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
