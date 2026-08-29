#!/usr/bin/env python3
"""Extract and validate reviewed Yahoo auction draft PDF exports."""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import tempfile
import json
import unicodedata
from collections import Counter
from pathlib import Path

ROW = re.compile(
    r"^\s*(?P<pick>\d+)\.\s+(?P<player>.+?)\s+\(.+? - (?P<position>QB|RB|WR|TE|K|DEF)\)"
    r"\s+\$(?P<salary>\d+)\s+(?P<owner>.+?)\s*$",
    re.MULTILINE,
)
ESPN_PLAYER = re.compile(
    r"^\s{20,}(?P<player>[^\n$]+?)\s*$\n\s+\$(?P<salary>\d+)\s*$\n\s{20,}[^\n]+?\s*$",
    re.MULTILINE,
)
ESPN_HEADING = re.compile(r"^\s{10,}(?P<owner>[A-Z][A-Z0-9 '&.\-]+)\s*$", re.MULTILINE)
POSITION_OVERRIDES = {
    "deanthonythomas": "WR", "devinfunchess": "WR", "mikebadgley": "K",
    "robbyanderson": "WR", "willfuller": "WR",
}


def pdf_text(path: Path) -> str:
    executable = os.environ.get("PDFTOTEXT") or shutil.which("pdftotext")
    if not executable:
        raise RuntimeError("pdftotext is required for stable Yahoo table extraction")
    with tempfile.NamedTemporaryFile(suffix=".txt") as output:
        subprocess.run([executable, "-layout", str(path), output.name], check=True)
        return Path(output.name).read_text()


def extract(path: Path, season: int) -> list[dict[str, str]]:
    text = pdf_text(path)
    rows = []
    for match in ROW.finditer(text):
        rows.append({
            "Season": str(season), "FF Team": match["owner"].strip(),
            "Pos": match["position"], "Player": match["player"].strip(),
            # The PDFs were printed years later and display last-career NFL teams.
            "Team": "", "Salary": f"${int(match['salary'])}",
            "_pick": match["pick"],
        })
    return rows


def extract_espn(path: Path, season: int) -> list[dict[str, str]]:
    text = pdf_text(path)
    headings = list(ESPN_HEADING.finditer(text))
    rows = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        players = list(ESPN_PLAYER.finditer(text[heading.end():end]))
        if len(players) != 14:
            continue
        for pick, player in enumerate(players, start=1):
            rows.append({
                "Season": str(season), "FF Team": heading["owner"].strip(),
                "Pos": "DEF" if player["player"].strip().endswith("D/ST") else "",
                "Player": player["player"].strip().removesuffix(" D/ST"), "Team": "",
                "Salary": f"${int(player['salary'])}", "_pick": f"{heading['owner']}:{pick}",
            })
    return rows


def normalized_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().casefold()
    value = re.sub(r"\b(?:jr|sr|ii|iii|iv|v)\b", "", value)
    return re.sub(r"[^a-z0-9]+", "", value)


def fill_positions(root: Path, rows: list[dict[str, str]]) -> None:
    positions: dict[str, set[str]] = {}
    for pointer in (root / "data" / "processed" / "canonical_projections").glob("*/latest.json"):
        reference = json.loads(pointer.read_text())
        payload = json.loads((root / reference["artifact"]).read_text())
        for player in payload["players"]:
            positions.setdefault(normalized_name(player["name"]), set()).add(player["position"])
    for row in rows:
        if row["Pos"]:
            continue
        candidates = positions.get(normalized_name(row["Player"]), set())
        if len(candidates) == 1:
            row["Pos"] = next(iter(candidates))
        elif normalized_name(row["Player"]) in POSITION_OVERRIDES:
            row["Pos"] = POSITION_OVERRIDES[normalized_name(row["Player"])]


def validate(rows: list[dict[str, str]], season: int) -> None:
    picks = [row["_pick"] for row in rows]
    owners = Counter(row["FF Team"] for row in rows)
    salaries = [int(row["Salary"][1:]) for row in rows]
    problems = []
    if len(rows) != 140 or len(set(picks)) != 140:
        problems.append(f"expected 140 unique picks, found {len(rows)} rows/{len(set(picks))} picks")
    if len(owners) != 10 or set(owners.values()) != {14}:
        problems.append(f"expected 10 teams with 14 players each, found {dict(owners)}")
    if any(salary <= 0 for salary in salaries):
        problems.append("found a non-positive salary")
    if any(row["Pos"] not in {"QB", "RB", "WR", "TE", "K", "DEF"} for row in rows):
        missing = sorted(row["Player"] for row in rows if not row["Pos"])
        problems.append(f"could not establish positions for {missing}")
    is_espn = any(row.get("_source") == "espn" for row in rows)
    valid_spend = 1900 <= sum(salaries) <= 2000 if is_espn else sum(salaries) == 2000
    if not valid_spend:
        problems.append(f"expected $2,000 total spend, found ${sum(salaries):,}")
    if problems:
        raise ValueError(f"{season} failed validation: {'; '.join(problems)}")


def run(root: Path, sources: list[tuple[int, Path]]) -> int:
    destination = root / "data" / "raw" / "auction_history.csv"
    with destination.open(encoding="utf-8-sig", newline="") as handle:
        existing = list(csv.DictReader(handle))
    keys = {(row["Season"], row["Player"].casefold(), row["Pos"]) for row in existing}
    added = []
    for season, path in sources:
        rows = extract_espn(path, season) if "espn" in path.name.casefold() else extract(path, season)
        for row in rows:
            row["_source"] = "espn" if "espn" in path.name.casefold() else "yahoo"
        fill_positions(root, rows)
        validate(rows, season)
        for row in rows:
            key = (row["Season"], row["Player"].casefold(), row["Pos"])
            if key not in keys:
                added.append({key: row[key] for key in ("Season", "FF Team", "Pos", "Player", "Team", "Salary")})
                keys.add(key)
    with destination.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=("Season", "FF Team", "Pos", "Player", "Team", "Salary"), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(existing + added)
    return len(added)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("source", nargs="+", help="SEASON=PDF")
    args = parser.parse_args()
    sources = [(int(value.split("=", 1)[0]), Path(value.split("=", 1)[1])) for value in args.source]
    print(f"Added {run(args.root.resolve(), sources)} auction sales")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
