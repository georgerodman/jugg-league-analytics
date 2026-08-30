#!/usr/bin/env python3
"""Run the guarded, season-aware data refresh without activating a draft."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

try:
    from scripts.rebuild_all import pointers, restore_pointers
    from scripts.season_refresh_plan import build_plan
    from scripts.season_rollover_readiness import readiness
except ModuleNotFoundError:  # Direct `python scripts/season_refresh.py` execution.
    from rebuild_all import pointers, restore_pointers
    from season_refresh_plan import build_plan
    from season_rollover_readiness import readiness


ROOT = Path(__file__).resolve().parents[1]


class RefreshError(RuntimeError):
    pass


def execution_preflight(
    root: Path,
    season: int,
    confirmation: str,
    archive_confirmed: bool,
    environ: dict[str, str] | os._Environ[str] = os.environ,
) -> dict[str, Any]:
    plan = build_plan(root, season)
    if plan["summary"]["blockers"]:
        raise RefreshError("Refresh plan contains blockers; review the dry-run report first")
    if confirmation != f"REFRESH-{season}":
        raise RefreshError(f"Confirmation must exactly equal REFRESH-{season}")
    if not archive_confirmed:
        raise RefreshError("Confirm that the external historical model-data archive is available")
    pdf = root / "data" / "raw" / "espn_cheat_sheets" / f"espn_salary_cap_values_{season}_non_ppr.pdf"
    if not pdf.is_file():
        raise RefreshError(f"Missing target-season ESPN salary-cap PDF: {pdf.relative_to(root)}")
    if not environ.get("FANTASYPROS_API_KEY"):
        raise RefreshError("FANTASYPROS_API_KEY is not available in the environment")
    return plan


def executable_commands(plan: dict[str, Any]) -> list[tuple[str, list[str]]]:
    return [
        (item["name"], item["command"])
        for item in plan["steps"]
        if item.get("command") and item["name"] != "rollover_readiness"
    ]


def run_commands(
    root: Path,
    commands: list[tuple[str, list[str]]],
    output: Path,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> list[dict[str, Any]]:
    before = pointers(root)
    records: list[dict[str, Any]] = []
    output.mkdir(parents=True, exist_ok=False)
    try:
        for name, command in commands:
            effective = [sys.executable, *command[1:]] if command[0] == "python3" else command
            result = runner(effective, cwd=root, capture_output=True, text=True)
            (output / f"{name}.log").write_text(result.stdout + result.stderr, encoding="utf-8")
            records.append({"name": name, "command": command, "exitCode": result.returncode})
            if result.returncode:
                raise RefreshError(f"Stage failed: {name}; see {output / f'{name}.log'}")
        return records
    except Exception:
        restore_pointers(root, before)
        raise


def execute(
    root: Path,
    season: int,
    confirmation: str,
    archive_confirmed: bool,
    environ: dict[str, str] | os._Environ[str] = os.environ,
) -> Path:
    plan = execution_preflight(root, season, confirmation, archive_confirmed, environ)
    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    output = root / ".local" / "refresh-runs" / f"{season}-{run_id}"
    before = pointers(root)
    try:
        records = run_commands(root, executable_commands(plan), output)
        report = readiness(root, season)
        (output / "readiness.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if not report["ready"]:
            raise RefreshError(f"Refresh stages completed but readiness failed; see {output / 'readiness.json'}")
    except Exception:
        restore_pointers(root, before)
        raise
    manifest = {
        "schemaVersion": 1,
        "season": season,
        "startedAt": started.isoformat(),
        "completedAt": datetime.now(timezone.utc).isoformat(),
        "status": "prepared_not_activated",
        "stages": records,
        "readiness": "readiness.json",
        "safety": "The active-season configuration, draft databases, and Google Sheets were not changed.",
    }
    manifest_path = output / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--execute", action="store_true", help="Run acquisition and model stages; default is dry-run only")
    parser.add_argument("--confirm", default="")
    parser.add_argument("--archive-confirmed", action="store_true")
    args = parser.parse_args()
    if not args.execute:
        plan = build_plan(ROOT, args.season)
        print(json.dumps(plan, indent=2))
        return 0
    try:
        print(f"Refresh prepared: {execute(ROOT, args.season, args.confirm, args.archive_confirmed)}")
    except (OSError, KeyError, ValueError, json.JSONDecodeError, RefreshError) as error:
        print(f"Refresh stopped safely: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
