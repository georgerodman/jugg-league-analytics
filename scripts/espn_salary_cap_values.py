#!/usr/bin/env python3
"""Extract and identity-match ESPN non-PPR salary-cap cheat-sheet PDFs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_canonical_projections import normalize_name, normalize_position, normalize_team

SCHEMA_VERSION = 1
SOURCE_PATTERN = re.compile(r"espn_salary_cap_values_(20\d{2})_non_ppr\.pdf$")
RANK_PATTERN = re.compile(r"(\d+)\.")
OVERALL_PATTERN = re.compile(r"\((\d+)\)")
POSITION_PATTERN = re.compile(r"\((QB|RB|WR|TE|K|D/ST|DST|DEF)(\d+)\)")
TEAM_PATTERN = re.compile(r"[A-Z]{2,3}")
SALARY_PATTERN = re.compile(r"\$(\d+)")
CSV_FIELDS = [
    "season", "source", "scoring", "teams", "budget_per_team", "overall_rank",
    "position", "position_rank", "player_name", "nfl_team", "salary_cap_value",
    "bye_week", "internal_player_id", "fantasypros_id", "identity_status",
    "match_method", "match_confidence", "source_pdf", "source_sha256",
]
DEFENSE_TEAMS = {
    "49ers": "SF", "Bears": "CHI", "Bengals": "CIN", "Bills": "BUF", "Broncos": "DEN",
    "Browns": "CLE", "Buccaneers": "TB", "Cardinals": "ARI", "Chargers": "LAC",
    "Chiefs": "KC", "Colts": "IND", "Commanders": "WAS", "Cowboys": "DAL", "Dolphins": "MIA",
    "Eagles": "PHI", "Falcons": "ATL", "Giants": "NYG", "Jaguars": "JAX", "Jets": "NYJ",
    "Lions": "DET", "Packers": "GB", "Panthers": "CAR", "Patriots": "NE", "Raiders": "LV",
    "Rams": "LAR", "Ravens": "BAL", "Saints": "NO", "Seahawks": "SEA", "Steelers": "PIT",
    "Texans": "HOU", "Titans": "TEN", "Vikings": "MIN",
    "WFT": "WAS",
}


class PipelineError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_canonical(root: Path, season: int) -> list[dict[str, Any]]:
    pointer_path = root / "data" / "processed" / "canonical_projections" / str(season) / "latest.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    return json.loads((root / pointer["artifact"]).read_text(encoding="utf-8"))["players"]


def line_words(words: list[dict[str, Any]], target: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted((word for word in words if abs(word["top"] - target["top"]) < 1.0), key=lambda word: word["x0"])


def single_content_page_words(pages: list[Any], filename: str) -> list[dict[str, Any]]:
    """Return the one populated cheat-sheet page, ignoring blank export pages."""
    populated = [words for page in pages if (words := page.extract_words())]
    if len(populated) != 1:
        raise PipelineError(f"{filename}: expected one populated page, found {len(populated)}")
    return populated[0]


def extract_rows(path: Path, season: int) -> list[dict[str, Any]]:
    if season == 2020:
        executable = shutil.which("pdftotext")
        if not executable:
            raise PipelineError("pdftotext is required for the 2020 four-column sheet")
        text = subprocess.run([executable, "-layout", str(path), "-"], check=True, capture_output=True, text=True).stdout
        pattern = re.compile(r"(\d+)\.\s+\((QB|RB|WR|TE|K|D/ST|DST|DEF)(\d+)\)\s+(.+?),\s+([A-Z]{2,3})\s+\$(\d+)\s+(\d+)")
        by_rank: dict[int, dict[str, Any]] = {}
        for match in pattern.finditer(text):
            overall = int(match.group(1))
            by_rank.setdefault(overall, {
                "season": season, "overall_rank": overall,
                "position": normalize_position(match.group(2)), "position_rank": int(match.group(3)),
                "player_name": match.group(4).strip(), "nfl_team": normalize_team(match.group(5)),
                "salary_cap_value": int(match.group(6)), "bye_week": int(match.group(7)),
            })
        return [by_rank[rank] for rank in sorted(by_rank)]

    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover - exercised by the CLI environment
        raise PipelineError("Install data dependencies first: python3 -m pip install -r requirements-data.txt") from exc

    with pdfplumber.open(path) as pdf:
        words = single_content_page_words(pdf.pages, path.name)

    rows: list[dict[str, Any]] = []
    for salary_word in (word for word in words if SALARY_PATTERN.fullmatch(word["text"])):
        same_line = line_words(words, salary_word)
        salary_index = same_line.index(salary_word)
        starts = [index for index, word in enumerate(same_line[:salary_index]) if RANK_PATTERN.fullmatch(word["text"])]
        if not starts:
            continue  # The explanatory $200 budget note.
        start = starts[-1]
        segment = same_line[start:salary_index]
        salary_digits = SALARY_PATTERN.fullmatch(salary_word["text"]).group(1)
        if salary_index + 1 < len(same_line) and same_line[salary_index + 1]["text"].isdigit():
            salary_value = int(salary_digits)
            bye_week = int(same_line[salary_index + 1]["text"])
        else:
            splits = [
                (int(salary_digits[:-width]), int(salary_digits[-width:]))
                for width in (2, 1)
                if len(salary_digits) > width and 4 <= int(salary_digits[-width:]) <= 14
            ]
            if not splits:
                raise PipelineError(f"{path.name}: missing bye week near {salary_word['text']} at y={salary_word['top']}")
            salary_value, bye_week = splits[0]
        position_token = next((POSITION_PATTERN.fullmatch(word["text"]) for word in segment[1:3] if POSITION_PATTERN.fullmatch(word["text"])), None)
        overall_token = next((OVERALL_PATTERN.fullmatch(word["text"]) for word in segment[1:3] if OVERALL_PATTERN.fullmatch(word["text"])), None)
        if not position_token and not overall_token:
            raise PipelineError(f"{path.name}: missing rank token in {' '.join(word['text'] for word in segment)}")
        name_start = 2
        segment_text = " ".join(word["text"] for word in segment)
        if "D/ST" in segment_text:
            week_index = next((index for index, word in enumerate(segment) if word["text"].startswith("(Wk")), len(segment))
            player_name = " ".join(word["text"] for word in segment[name_start:week_index]).rstrip(",")
            nickname = player_name.replace(" D/ST", "")
            nfl_team = DEFENSE_TEAMS.get(nickname)
            if not nfl_team:
                raise PipelineError(f"{path.name}: unknown defense name {player_name}")
        else:
            team_index = len(segment) - 1
            while team_index > 1 and not TEAM_PATTERN.fullmatch(segment[team_index]["text"].rstrip(",")):
                team_index -= 1
            if team_index <= 1:
                raise PipelineError(f"{path.name}: missing team in {segment_text}")
            player_name = " ".join(word["text"] for word in segment[name_start:team_index]).rstrip(",")
            nfl_team = normalize_team(segment[team_index]["text"].rstrip(","))
        row = {
            "season": season,
            "overall_rank": int(RANK_PATTERN.fullmatch(segment[0]["text"]).group(1)) if position_token else int(overall_token.group(1)),
            "position": normalize_position(position_token.group(1)) if position_token else None,
            "position_rank": int(position_token.group(2)) if position_token else int(RANK_PATTERN.fullmatch(segment[0]["text"]).group(1)),
            "player_name": player_name,
            "nfl_team": nfl_team,
            "salary_cap_value": salary_value,
            "bye_week": bye_week,
        }
        rows.append(row)
    return rows


def load_name_aliases(root: Path, season: int) -> dict[str, str]:
    payload = json.loads((root / "config" / "player_aliases.json").read_text(encoding="utf-8"))
    aliases = {}
    for entry in payload.get("aliases", []):
        if entry.get("seasons") and season not in entry["seasons"]:
            continue
        target = entry.get("fantasypros_name") or entry.get("registry_name")
        if target:
            aliases[normalize_name(entry["source_name"])] = normalize_name(target)
    return aliases


def load_nflverse_registry(root: Path) -> dict[str, list[dict[str, Any]]]:
    latest = json.loads((root / "data" / "processed" / "nflverse" / "latest.json").read_text(encoding="utf-8"))
    path = (root / latest["manifest"]).parent / "players.csv"
    registry: dict[str, list[dict[str, Any]]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for player in csv.DictReader(handle):
            if player.get("gsis_id"):
                registry.setdefault(normalize_name(player["display_name"]), []).append(player)
    return registry


def match_rows(rows: list[dict[str, Any]], canonical: list[dict[str, Any]], global_canonical: list[dict[str, Any]], aliases: dict[str, str], registry: dict[str, list[dict[str, Any]]]) -> None:
    by_name: dict[str, list[dict[str, Any]]] = {}
    by_name_pos: dict[tuple[str, str], list[dict[str, Any]]] = {}
    defenses_by_team: dict[str | None, list[dict[str, Any]]] = {}
    for player in canonical:
        name = normalize_name(player["name"])
        position = normalize_position(player["position"])
        by_name.setdefault(name, []).append(player)
        by_name_pos.setdefault((name, position), []).append(player)
        if position == "DEF":
            defenses_by_team.setdefault(normalize_team(player.get("nfl_team")), []).append(player)
    global_by_name: dict[str, dict[str, dict[str, Any]]] = {}
    for player in global_canonical:
        global_by_name.setdefault(normalize_name(player["name"]), {})[player["internal_player_id"]] = player

    for row in rows:
        source_name = normalize_name(row["player_name"].replace("D/ST", ""))
        name = source_name
        candidates = by_name.get(name, [])
        if row["position"]:
            candidates = by_name_pos.get((name, row["position"]), [])
        if not candidates and source_name in aliases:
            name = aliases[source_name]
            candidates = by_name.get(name, [])
            if row["position"]:
                candidates = by_name_pos.get((name, row["position"]), [])
        if len(candidates) == 1:
            match, method, confidence = candidates[0], "exact_name_position" if row["position"] else "exact_name", 0.95
        elif "D/ST" in row["player_name"] and len(defenses_by_team.get(row["nfl_team"], [])) == 1:
            match, method, confidence = defenses_by_team[row["nfl_team"]][0], "exact_defense_team", 1.0
        elif len(candidates) > 1:
            team_candidates = [candidate for candidate in candidates if normalize_team(candidate.get("nfl_team")) == row["nfl_team"]]
            if len(team_candidates) == 1:
                match, method, confidence = team_candidates[0], "exact_name_team", 0.95
            else:
                match, method, confidence = None, "ambiguous_name", 0.0
        elif len(global_by_name.get(name, {})) == 1:
            match = next(iter(global_by_name[name].values()))
            method, confidence = "global_exact_name", 0.8
        elif len(registry.get(name, [])) == 1:
            registry_player = registry[name][0]
            row["position"] = normalize_position(registry_player["position"])
            row.update({
                "internal_player_id": f"nfl:gsis:{registry_player['gsis_id']}",
                "fantasypros_id": None, "identity_status": "stable",
                "match_method": "nflverse_exact_name", "match_confidence": 0.9,
            })
            continue
        else:
            match, method, confidence = None, "unmatched", 0.0
        if match:
            row["position"] = normalize_position(match["position"])
            row.update({
                "internal_player_id": match["internal_player_id"],
                "fantasypros_id": match["source_ids"].get("fantasypros"),
                "identity_status": match.get("identity_status"),
            })
        else:
            row.update({"internal_player_id": None, "fantasypros_id": None, "identity_status": None})
        row.update({"match_method": method, "match_confidence": confidence})


def validate(rows: list[dict[str, Any]], season: int) -> list[dict[str, Any]]:
    flags: list[dict[str, Any]] = []
    expected = 300 if season == 2020 else 280
    if len(rows) != expected:
        flags.append({"severity": "error", "type": "row_count", "season": season, "details": f"expected {expected}, extracted {len(rows)}"})
    overall = [row["overall_rank"] for row in rows]
    duplicates = sorted(rank for rank, count in Counter(overall).items() if count > 1)
    if duplicates:
        flags.append({"severity": "error", "type": "duplicate_overall_rank", "season": season, "details": duplicates})
    for row in rows:
        if row["match_method"] in {"unmatched", "ambiguous_name"}:
            flags.append({
                "severity": "review", "type": row["match_method"], "season": season,
                "overall_rank": row["overall_rank"], "player_name": row["player_name"],
                "position": row["position"], "nfl_team": row["nfl_team"],
                "salary_cap_value": row["salary_cap_value"],
            })
        if not 0 <= row["salary_cap_value"] <= 200:
            flags.append({"severity": "error", "type": "salary_range", "season": season, "details": row})
    return flags


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in CSV_FIELDS} for row in rows)


def run(root: Path) -> Path:
    source_dir = root / "data" / "raw" / "espn_cheat_sheets"
    sources = []
    for path in sorted(source_dir.glob("*.pdf")):
        match = SOURCE_PATTERN.fullmatch(path.name)
        if not match:
            raise PipelineError(f"Non-canonical PDF filename: {path.name}")
        sources.append((int(match.group(1)), path))
    if not sources:
        raise PipelineError("No ESPN salary-cap PDFs found")

    built_at = datetime.now(timezone.utc)
    build_id = built_at.strftime("%Y%m%dT%H%M%SZ")
    all_rows, all_flags, season_metadata = [], [], []
    output_root = root / "data" / "processed" / "espn_salary_cap_values"
    global_canonical = [player for season, _ in sources for player in load_canonical(root, season)]
    registry = load_nflverse_registry(root)
    for season, path in sources:
        checksum = sha256(path)
        rows = extract_rows(path, season)
        rows = list({(row["overall_rank"], row["player_name"], row["salary_cap_value"]): row for row in rows}.values())
        match_rows(rows, load_canonical(root, season), global_canonical, load_name_aliases(root, season), registry)
        for row in rows:
            row.update({
                "source": "espn", "scoring": "non_ppr", "teams": 10, "budget_per_team": 200,
                "source_pdf": str(path.relative_to(root)), "source_sha256": checksum,
            })
        flags = validate(rows, season)
        methods = Counter(row["match_method"] for row in rows)
        metadata = {
            "season": season, "row_count": len(rows), "matched_count": sum(method != "unmatched" and method != "ambiguous_name" for method in methods.elements()),
            "match_methods": dict(methods), "salary_total": sum(row["salary_cap_value"] for row in rows),
            "source_pdf": str(path.relative_to(root)), "source_sha256": checksum,
        }
        out_dir = output_root / str(season) / build_id
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = {"metadata": {"schema_version": SCHEMA_VERSION, "build_id": build_id, "built_at": built_at.isoformat(), **metadata}, "values": rows, "flags": flags}
        json_path = out_dir / "espn_salary_cap_values.json"
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_csv(out_dir / "espn_salary_cap_values.csv", rows)
        (output_root / str(season) / "latest.json").write_text(json.dumps({"schema_version": SCHEMA_VERSION, "build_id": build_id, "artifact": str(json_path.relative_to(root))}, indent=2) + "\n")
        all_rows.extend(rows)
        all_flags.extend(flags)
        season_metadata.append(metadata)

    combined_dir = output_root / "combined" / build_id
    combined_dir.mkdir(parents=True, exist_ok=True)
    write_csv(combined_dir / "espn_salary_cap_values.csv", all_rows)
    (combined_dir / "espn_salary_cap_values.json").write_text(json.dumps({"metadata": {"schema_version": SCHEMA_VERSION, "build_id": build_id, "built_at": built_at.isoformat(), "seasons": season_metadata}, "values": all_rows}, indent=2, sort_keys=True) + "\n")
    flag_fields = ["severity", "type", "season", "overall_rank", "player_name", "position", "nfl_team", "salary_cap_value", "details"]
    with (combined_dir / "validation_flags.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=flag_fields)
        writer.writeheader()
        writer.writerows({field: flag.get(field) for field in flag_fields} for flag in all_flags)
    (combined_dir / "validation_flags.json").write_text(json.dumps({"metadata": {"schema_version": SCHEMA_VERSION, "build_id": build_id}, "flags": all_flags}, indent=2, sort_keys=True) + "\n")
    manifest = combined_dir / "manifest.json"
    manifest.write_text(json.dumps({"schema_version": SCHEMA_VERSION, "build_id": build_id, "built_at": built_at.isoformat(), "seasons": season_metadata, "flag_count": len(all_flags)}, indent=2, sort_keys=True) + "\n")
    (output_root / "combined" / "latest.json").write_text(json.dumps({"schema_version": SCHEMA_VERSION, "build_id": build_id, "manifest": str(manifest.relative_to(root))}, indent=2) + "\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        print(f"Wrote {run(args.root.resolve())}")
    except (OSError, KeyError, ValueError, json.JSONDecodeError, PipelineError) as exc:
        print(f"ESPN salary-cap import failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
