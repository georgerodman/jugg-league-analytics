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

Generate the annual import/model plan first:

```sh
python3 scripts/season_refresh_plan.py --season 2027
```

This writes `.local/readiness/refresh-2027.json`. It records the ordered data
imports and manual prerequisites without running a download or changing any
live state. The collectors and the auction-price and production-value builders
accept an explicit target season; model builders use completed prior seasons as
their training and backtest window.

After the new artifacts have been generated, run the rollover gate:

When the archive and target-season ESPN PDF are available and the FantasyPros
credential is configured, the guarded refresh can run the listed stages:

```sh
python3 scripts/season_refresh.py --season 2027 --execute \
  --confirm REFRESH-2027 --archive-confirmed
```

It writes stage logs under `.local/refresh-runs/`, stops at the first failure,
and restores previously published artifact pointers on failure. A successful
run prepares and verifies artifacts only. It cannot activate the new season,
create a draft database, or enable/contact Google Sheets.

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
