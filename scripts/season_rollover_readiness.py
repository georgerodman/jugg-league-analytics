#!/usr/bin/env python3
"""Report whether a new JUGG season can be prepared without changing active state."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check(name: str, status: str, message: str, path: str | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"name": name, "status": status, "message": message}
    if path is not None:
        result["path"] = path
    return result


def inspect_active_draft(root: Path, active: dict[str, Any]) -> list[dict[str, Any]]:
    database = root / active["databasePath"]
    if not database.is_file():
        return [check("active_database", "blocker", "The configured active database does not exist.", active["databasePath"])]
    try:
        connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        row = connection.execute(
            "SELECT id,season,status,finalized_at,finalized_backup_path,google_sheets_sync_enabled FROM drafts WHERE id=?",
            (active["draftId"],),
        ).fetchone()
        connection.close()
    except sqlite3.Error as error:
        return [check("active_database", "blocker", f"The active database could not be inspected: {error}", active["databasePath"])]
    if row is None:
        return [check("active_draft", "blocker", "The configured draft ID is absent from the active database.", active["databasePath"])]
    draft_id, season, status, finalized_at, backup_path, sheets_enabled = row
    checks = [
        check("active_identity", "pass" if draft_id == active["draftId"] and season == active["season"] else "blocker", f"Active database contains {draft_id} for {season}."),
        check("active_finalized", "pass" if status == "complete" and finalized_at else "blocker", f"Active draft status is {status}; finalized at {finalized_at or 'not recorded'}."),
        check("active_sheet_disconnected", "pass" if not sheets_enabled else "blocker", "Google Sheets synchronization is disabled for the finalized draft." if not sheets_enabled else "Google Sheets synchronization is still enabled."),
    ]
    backup = Path(backup_path) if backup_path else None
    checks.append(
        check(
            "active_final_backup",
            "pass" if backup and backup.is_file() else "blocker",
            "The final SQLite backup is present." if backup and backup.is_file() else "The recorded final SQLite backup is missing.",
            str(backup) if backup else None,
        )
    )
    return checks


def target_artifacts(season: int) -> dict[str, str]:
    return {
        "canonical_projections": f"data/processed/canonical_projections/{season}/latest.json",
        "fantasypros_adp": f"data/processed/fantasypros_adp/{season}/latest.json",
        "espn_salary_cap_values": f"data/processed/espn_salary_cap_values/{season}/latest.json",
        "nflverse_depth_charts": f"data/processed/nflverse_depth_charts/{season}/latest.json",
        "fantasypros_context": f"data/processed/fantasypros_context/{season}/latest.json",
        "decision_board": "data/processed/production_value_model/latest.json",
        "owner_profiles": "data/processed/owner_tendencies/latest.json",
    }


def inspect_target(root: Path, active: dict[str, Any], season: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    draft_id = f"jugg-{season}"
    database_path = f".local/renegade-draft-room-{season}.sqlite"
    sheet_path = f"config/google_sheets_{season}.json"
    proposed = {
        "schemaVersion": 1,
        "season": season,
        "draftId": draft_id,
        "draftName": f"{season} JUGG Auction",
        "databasePath": database_path,
        "googleSheetsConfigPath": sheet_path,
    }
    checks = [
        check("target_is_future", "pass" if season > active["season"] else "blocker", f"Target season {season} must be later than active season {active['season']}."),
        check("target_draft_distinct", "pass" if draft_id != active["draftId"] else "blocker", f"Proposed draft ID is {draft_id}."),
        check("target_database_distinct", "pass" if database_path != active["databasePath"] else "blocker", f"Proposed database is {database_path}."),
        check("target_database_unused", "pass" if not (root / database_path).exists() else "blocker", "The proposed database path is unused." if not (root / database_path).exists() else "The proposed database already exists.", database_path),
    ]
    for name, relative in target_artifacts(season).items():
        path = root / relative
        if not path.is_file():
            checks.append(check(f"artifact_{name}", "blocker", f"Target-season artifact is not ready: {name}.", relative))
            continue
        if name == "owner_profiles":
            checks.append(check(f"artifact_{name}", "pass", "Reusable owner profiles are present.", relative))
            continue
        try:
            payload = load_json(path)
            serialized = json.dumps(payload)
            season_matches = str(season) in serialized
        except (OSError, json.JSONDecodeError) as error:
            checks.append(check(f"artifact_{name}", "blocker", f"Artifact pointer is unreadable: {error}", relative))
            continue
        checks.append(check(f"artifact_{name}", "pass" if season_matches else "blocker", f"Artifact pointer {'contains' if season_matches else 'does not contain'} target-season evidence.", relative))
    sheet_exists = (root / sheet_path).is_file()
    checks.append(
        check(
            "target_sheet_mapping",
            "warning" if not sheet_exists else "pass",
            "No new Sheet mapping exists; the new draft must remain disconnected." if not sheet_exists else "A target-season Sheet mapping exists and still requires human review.",
            sheet_path,
        )
    )
    return checks, proposed


def readiness(root: Path, season: int) -> dict[str, Any]:
    active_path = root / "config" / "active-season.json"
    active = load_json(active_path)
    checks = inspect_active_draft(root, active)
    target_checks, proposed = inspect_target(root, active, season)
    checks.extend(target_checks)
    blockers = [item for item in checks if item["status"] == "blocker"]
    warnings = [item for item in checks if item["status"] == "warning"]
    return {
        "schemaVersion": 1,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "mode": "dry_run",
        "active": active,
        "target": proposed,
        "ready": not blockers,
        "summary": {"passed": sum(item["status"] == "pass" for item in checks), "warnings": len(warnings), "blockers": len(blockers)},
        "checks": checks,
        "nextActions": [item["message"] for item in blockers] or ["All gates pass. A separate apply step may prepare the season."],
        "safety": "No configuration, database, artifact pointer, or Google Sheet was changed.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = readiness(ROOT, args.season)
    output = args.output or ROOT / ".local" / "readiness" / f"season-{args.season}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(output), "ready": report["ready"], **report["summary"], "safety": report["safety"]}, indent=2))


if __name__ == "__main__":
    main()
