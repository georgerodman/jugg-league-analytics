#!/usr/bin/env python3
"""Create a durable, human-readable archive of a finalized draft."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = ROOT / ".local" / "renegade-draft-room.sqlite"
DEFAULT_ARCHIVE_ROOT = ROOT / ".local" / "archives"


EXPORTS = {
    "teams.csv": """
        SELECT o.display_name AS owner, t.display_name AS team,
               s.remaining_budget, s.rostered_player_count, s.open_slot_count
        FROM teams t
        JOIN owners o ON o.id = t.owner_id
        JOIN team_draft_state s ON s.team_id = t.id
        WHERE t.draft_id = ?
        ORDER BY o.display_name
    """,
    "rosters.csv": """
        SELECT o.display_name AS owner, t.display_name AS team,
               rs.slot_type, rs.ordinal, p.display_name AS player,
               p.position, p.nfl_team, sales.price
        FROM teams t
        JOIN owners o ON o.id = t.owner_id
        JOIN roster_slots rs ON rs.team_id = t.id
        LEFT JOIN players p ON p.id = rs.player_id
        LEFT JOIN sales ON sales.id = rs.filled_sale_id
                         AND sales.voided_event_id IS NULL
        WHERE t.draft_id = ?
        ORDER BY o.display_name, rs.slot_type, rs.ordinal
    """,
    "sales.csv": """
        SELECT event.sequence AS sale_sequence, sales.recorded_at,
               p.display_name AS player, p.position, p.nfl_team,
               o.display_name AS winning_owner, t.display_name AS winning_team,
               sales.price, rs.slot_type, rs.ordinal
        FROM sales
        JOIN draft_events event ON event.id = sales.recorded_event_id
        JOIN players p ON p.id = sales.player_id
        JOIN teams t ON t.id = sales.winner_team_id
        JOIN owners o ON o.id = t.owner_id
        LEFT JOIN roster_slots rs ON rs.id = sales.roster_slot_id
        WHERE sales.draft_id = ? AND sales.voided_event_id IS NULL
        ORDER BY event.sequence
    """,
    "events.csv": """
        SELECT sequence, event_type, aggregate_type, aggregate_id,
               idempotency_key, payload_json, occurred_at, recorded_at
        FROM draft_events
        WHERE draft_id = ?
        ORDER BY sequence
    """,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_metadata() -> dict[str, Any]:
    def run(*args: str) -> str:
        try:
            return subprocess.check_output(
                ["git", *args], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return "unknown"

    status = run("status", "--porcelain")
    return {"commit": run("rev-parse", "HEAD"), "working_tree_dirty": bool(status and status != "unknown")}


def export_csv(connection: sqlite3.Connection, query: str, draft_id: str, destination: Path) -> int:
    cursor = connection.execute(query, (draft_id,))
    rows = cursor.fetchall()
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([column[0] for column in cursor.description])
        writer.writerows(rows)
    return len(rows)


def validate_finalized_draft(connection: sqlite3.Connection, draft_id: str) -> sqlite3.Row:
    integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity}")
    draft = connection.execute(
        """SELECT id, season, name, status, state_version, finalized_at,
                  finalized_backup_path, google_sheets_sync_enabled
           FROM drafts WHERE id = ?""",
        (draft_id,),
    ).fetchone()
    if draft is None:
        raise RuntimeError(f"Draft {draft_id!r} was not found")
    if draft["status"] != "complete":
        raise RuntimeError(f"Draft {draft_id!r} is not finalized")
    if draft["google_sheets_sync_enabled"] != 0:
        raise RuntimeError("Google Sheets synchronization is still enabled")
    open_nominations = connection.execute(
        "SELECT COUNT(*) FROM nominations WHERE draft_id = ? AND status = 'open'", (draft_id,)
    ).fetchone()[0]
    incomplete_teams = connection.execute(
        """SELECT COUNT(*) FROM team_draft_state
           WHERE team_id IN (SELECT id FROM teams WHERE draft_id = ?)
             AND open_slot_count > 0""",
        (draft_id,),
    ).fetchone()[0]
    if open_nominations or incomplete_teams:
        raise RuntimeError("Finalized draft still has an open nomination or incomplete roster")
    return draft


def create_archive(database: Path, archive_root: Path, draft_id: str) -> Path:
    database = database.resolve()
    if not database.exists():
        raise FileNotFoundError(database)
    source = sqlite3.connect(database)
    source.row_factory = sqlite3.Row
    try:
        draft = validate_finalized_draft(source, draft_id)
        finalized_stamp = str(draft["finalized_at"]).replace("-", "").replace(":", "").replace(".", "")
        archive = archive_root.resolve() / f"{draft_id}-final-{finalized_stamp}"
        archive.mkdir(parents=True, exist_ok=False)

        backup = archive / "draft.sqlite"
        destination = sqlite3.connect(backup)
        try:
            source.backup(destination)
            destination.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            destination.execute("PRAGMA journal_mode = DELETE")
        finally:
            destination.close()
        for suffix in ("-wal", "-shm"):
            auxiliary = Path(f"{backup}{suffix}")
            if auxiliary.exists():
                auxiliary.unlink()

        counts: dict[str, int] = {}
        for filename, query in EXPORTS.items():
            counts[filename] = export_csv(source, query, draft_id, archive / filename)

        readme = archive / "README.md"
        readme.write_text(
            "\n".join(
                [
                    f"# {draft['name']} — Final Archive",
                    "",
                    f"- Draft ID: `{draft['id']}`",
                    f"- Season: {draft['season']}",
                    f"- Finalized: {draft['finalized_at']}",
                    f"- Final state version: {draft['state_version']}",
                    "- Google Sheets synchronization: disabled",
                    "",
                    "`draft.sqlite` is the authoritative self-contained record. The CSV files are readable exports for review and recovery.",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        files = {
            path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
            for path in sorted(archive.iterdir())
            if path.is_file()
        }
        manifest = {
            "schema_version": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "draft": dict(draft),
            "source_database": str(database),
            "git": git_metadata(),
            "export_row_counts": counts,
            "files": files,
        }
        (archive / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return archive
    except Exception:
        raise
    finally:
        source.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--archive-root", type=Path, default=DEFAULT_ARCHIVE_ROOT)
    parser.add_argument("--draft-id", default="jugg-2026")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    archive_path = create_archive(arguments.database, arguments.archive_root, arguments.draft_id)
    print(archive_path)
