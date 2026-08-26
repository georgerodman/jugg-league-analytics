#!/usr/bin/env python3
"""Ingest supplied FantasyPros PDF tables as versioned contextual research."""

import hashlib
import json
import re
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
BUILD = "20260826T235500Z"
BUILT_AT = "2026-08-26T23:55:00Z"
ANALYSIS_OUT = ROOT / "data/processed/fantasy_analysis" / BUILD
CONTEXT_OUT = ROOT / "data/processed/fantasy_context" / BUILD

FILES = {
    "player_targets": Path("/Users/george.rodman/Desktop/2025 Most Targeted Players _ FantasyPros.pdf"),
    "team_targets": Path("/Users/george.rodman/Desktop/2025 NFL Targets By Team _ FantasyPros.pdf"),
    "expert_accuracy": Path("/Users/george.rodman/Desktop/2025 Fantasy Football Accuracy Scores _ FantasyPros.pdf"),
    "strength_of_schedule": Path("/Users/george.rodman/Desktop/Fantasy Football Strength of Schedule (SOS) _ FantasyPros.pdf"),
    "rb_handcuffs": Path("/Users/george.rodman/Desktop/2026 Fantasy Football Handcuffs (Running Backs) _ FantasyPros.pdf"),
}

SOURCE_META = {
    "player_targets": ("2025 Most Targeted Players", "https://www.fantasypros.com/nfl/reports/targets/", "2025-12-31", "historical_player_usage", "Weekly and season-total 2025 targets for NFL receivers, tight ends, and running backs."),
    "team_targets": ("2025 NFL Targets By Team", "https://www.fantasypros.com/nfl/reports/targets-distribution/", "2025-12-31", "historical_team_usage", "2025 team target totals and positional target shares for WR, RB, and TE."),
    "expert_accuracy": ("2025 Fantasy Football Accuracy Scores", "https://www.fantasypros.com/nfl/accuracy/", "2025-12-31", "analyst_accuracy", "2025 overall and position-level expert accuracy ranks used as source-quality context."),
    "strength_of_schedule": ("Fantasy Football Strength of Schedule (SOS)", "https://www.fantasypros.com/nfl/strength-of-schedule.php", "2026-08-26", "strength_of_schedule", "FantasyPros' visual 2026 position-by-position strength-of-schedule chart; preserved as contextual evidence, not a player vote."),
    "rb_handcuffs": ("2026 Fantasy Football Handcuffs (Running Backs)", "https://www.fantasypros.com/nfl/running-back-handcuffs.php", "2026-08-26", "depth_chart", "Projected starting running back and primary handcuff for every NFL team, with ECR and ADP columns."),
}

TEAMS = [
    "Arizona Cardinals", "Atlanta Falcons", "Baltimore Ravens", "Buffalo Bills", "Carolina Panthers", "Chicago Bears", "Cincinnati Bengals", "Cleveland Browns", "Dallas Cowboys", "Denver Broncos", "Detroit Lions", "Green Bay Packers", "Houston Texans", "Indianapolis Colts", "Jacksonville Jaguars", "Kansas City Chiefs", "Los Angeles Chargers", "Los Angeles Rams", "Las Vegas Raiders", "Miami Dolphins", "Minnesota Vikings", "New England Patriots", "New Orleans Saints", "New York Giants", "New York Jets", "Philadelphia Eagles", "Pittsburgh Steelers", "Seattle Seahawks", "San Francisco 49ers", "Tampa Bay Buccaneers", "Tennessee Titans", "Washington Commanders",
]


def pages(path):
    with pdfplumber.open(path) as pdf:
        return [page.extract_text(x_tolerance=2, y_tolerance=2) or "" for page in pdf.pages]


def player_targets(text_pages):
    rows = []
    pattern = re.compile(r"^(.*?) (QB|RB|WR|TE) ([A-Z]{2,3}) (.*?) (\d+) ([0-9]+\.[0-9])$")
    for text in text_pages:
        for line in text.splitlines():
            match = pattern.match(line.strip())
            if match:
                rows.append({"player": match.group(1), "position": match.group(2), "team": match.group(3), "targets": int(match.group(5)), "targets_per_game": float(match.group(6))})
    unique = {(row["player"], row["team"]): row for row in rows}
    return sorted(unique.values(), key=lambda row: (-row["targets"], row["player"]))


def team_targets(text):
    rows = []
    pattern = re.compile(r"^(.+?) (\d+) ([0-9.]+%) (\d+) ([0-9.]+%) (\d+) ([0-9.]+%) (\d+)$")
    for line in text.splitlines():
        match = pattern.match(line.strip())
        if match and match.group(1) in TEAMS:
            rows.append({"team": match.group(1), "wr_targets": int(match.group(2)), "wr_share": match.group(3), "rb_targets": int(match.group(4)), "rb_share": match.group(5), "te_targets": int(match.group(6)), "te_share": match.group(7), "total_targets": int(match.group(8))})
    return rows


def expert_accuracy(text_pages):
    rows = []
    pattern = re.compile(r"^(\d+) (.+?) ([—\d]+) ([—\d]+) ([—\d]+) ([—\d]+) ([—\d]+) ([—\d]+) ([—\d]+)$")
    for text in text_pages:
        for line in text.splitlines():
            match = pattern.match(line.strip())
            if match:
                values = [None if value == "—" else int(value) for value in match.groups()[2:]]
                rows.append({"overall_rank": int(match.group(1)), "expert": match.group(2), **dict(zip(("qb_rank", "rb_rank", "wr_rank", "te_rank", "k_rank", "dst_rank", "idp_rank"), values))})
    return rows


def handcuffs(text):
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        team = next((name for name in TEAMS if stripped.startswith(name + " ")), None)
        if not team:
            continue
        tokens = stripped[len(team) + 1:].split()
        first_number = next((index for index, token in enumerate(tokens) if token.isdigit()), None)
        if first_number is None:
            continue
        starter = " ".join(tokens[:first_number])
        starter_ecr = int(tokens[first_number])
        remainder = tokens[first_number + 1:]
        if remainder[:1] == ["—"]:
            handcuff, handcuff_ecr = None, None
        else:
            second_number = next((index for index, token in enumerate(remainder) if token.isdigit()), None)
            if second_number is None:
                continue
            handcuff = " ".join(remainder[:second_number])
            handcuff_ecr = int(remainder[second_number])
        rows.append({"team": team, "projected_starter": starter, "starter_ecr": starter_ecr, "handcuff": handcuff, "handcuff_ecr": handcuff_ecr, "adp": None})
    return rows


def source_artifact(key, path):
    title, url, published_at, content_type, summary = SOURCE_META[key]
    source_id = f"fantasypros:pdf:{key}:2026-08-26"
    return {
        "metadata": {"schema_version": 2, "build_id": BUILD, "built_at": BUILT_AT, "season": 2026, "takeaway_count": 0},
        "source": {"id": source_id, "source_key": "fantasypros", "title": title, "author": "FantasyPros", "url": url, "published_at": published_at, "season": 2026, "content_type": content_type, "summary": summary},
        "takeaways": [],
    }


def main():
    for path in FILES.values():
        if not path.exists():
            raise FileNotFoundError(path)
    extracted = {key: pages(path) for key, path in FILES.items()}
    context = {
        "metadata": {"schema_version": 1, "build_id": BUILD, "built_at": BUILT_AT},
        "datasets": {
            "player_targets_2025": {"source_id": "fantasypros:pdf:player_targets:2026-08-26", "rows": player_targets(extracted["player_targets"])},
            "team_targets_2025": {"source_id": "fantasypros:pdf:team_targets:2026-08-26", "rows": team_targets(extracted["team_targets"][0])},
            "expert_accuracy_2025": {"source_id": "fantasypros:pdf:expert_accuracy:2026-08-26", "rows": expert_accuracy(extracted["expert_accuracy"])},
            "strength_of_schedule_2026": {"source_id": "fantasypros:pdf:strength_of_schedule:2026-08-26", "rows": [{"team": team, "positions": ["QB", "RB", "WR", "TE", "K", "DST"], "encoding": "visual five-segment difficulty scale retained in source PDF"} for team in TEAMS]},
            "rb_handcuffs_2026": {"source_id": "fantasypros:pdf:rb_handcuffs:2026-08-26", "rows": handcuffs(extracted["rb_handcuffs"][0])},
        },
        "source_files": {key: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for key, path in FILES.items()},
    }
    ANALYSIS_OUT.mkdir(parents=True, exist_ok=True)
    CONTEXT_OUT.mkdir(parents=True, exist_ok=True)
    analysis_paths = []
    for key, path in FILES.items():
        artifact = source_artifact(key, path)
        filename = f"fantasypros_pdf_{key}.json"
        (ANALYSIS_OUT / filename).write_text(json.dumps(artifact, indent=2) + "\n")
        analysis_paths.append(f"data/processed/fantasy_analysis/{BUILD}/{filename}")
    context_path = CONTEXT_OUT / "fantasypros_pdf_context.json"
    context_path.write_text(json.dumps(context, indent=2) + "\n")
    analysis_pointer = ROOT / "data/processed/fantasy_analysis/latest.json"
    pointer = json.loads(analysis_pointer.read_text())
    pointer["artifacts"] = [item for item in pointer["artifacts"] if f"/{BUILD}/" not in item] + analysis_paths
    analysis_pointer.write_text(json.dumps(pointer, indent=2) + "\n")
    context_pointer = ROOT / "data/processed/fantasy_context/latest.json"
    context_pointer.parent.mkdir(parents=True, exist_ok=True)
    context_pointer.write_text(json.dumps({"schema_version": 1, "artifact": f"data/processed/fantasy_context/{BUILD}/fantasypros_pdf_context.json"}, indent=2) + "\n")
    print(json.dumps({"sources": len(FILES), "rows": {name: len(dataset["rows"]) for name, dataset in context["datasets"].items()}}))


if __name__ == "__main__":
    main()
