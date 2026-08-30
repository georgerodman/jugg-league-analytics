# Season Rollover

## Current boundary

The live Draft Room reads its active identity from
`config/active-season.json`. That file defines the season, draft ID, draft
name, local SQLite path, and Google Sheets mapping path. The server derives all
season-specific runtime artifact pointers from the configured season.

The current configuration intentionally remains on finalized `jugg-2026`.
Changing this file manually is not a supported rollover procedure: a new season
must not activate until its artifacts validate, its database path is new, and
its Google Sheets mapping is either absent or explicitly reviewed.

## Safe rollover sequence

The future guided rollover command must:

1. Require a four-digit target season later than the finalized active season.
2. Verify the current draft is finalized and has a readable final backup.
3. Refuse to reuse the current draft ID, database path, or finalized database.
4. Verify required target-season artifacts and owner configuration.
5. Create a distinct local SQLite database in setup state.
6. Start with Google Sheets synchronization disabled.
7. Accept a separately reviewed target-season Sheet mapping when supplied.
8. Run artifact, Python, domain, build, and isolated startup checks.
9. Update `config/active-season.json` only after every gate passes.
10. Preserve a rollback copy of the prior active-season configuration.

## Next implementation stop

Run the dry-run readiness report with:

```sh
python3 scripts/season_rollover_readiness.py --season 2027
```

It verifies the finalized active database and backup, confirms Sheets is
disabled, proposes distinct target paths, checks every required target-season
artifact, and records missing imports. It never changes active configuration,
creates a target database, advances an artifact pointer, or contacts Google.

The next implementation stop is the explicit preparation/apply command. It
must consume a passing readiness report and remain unable to activate a season
whose artifacts are incomplete.
