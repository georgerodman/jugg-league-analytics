# Start the Next JUGG Season

This is the short entry point for preparing a new draft season. The finalized
2026 draft remains read-only and disconnected throughout preparation.

## Before downloading anything

1. Keep the external finalized-draft archive and model-data archive available.
   They do not need to be copied back into the repository unless a missing
   historical input is reported.
2. Install dependencies only if they were removed: `npm install` and
   `python3 -m pip install -r requirements-data.txt`.
3. Put the FantasyPros credential in the ignored local `.env` file.
4. Obtain the new ESPN non-PPR salary-cap PDF and name it
   `data/raw/espn_cheat_sheets/espn_salary_cap_values_<season>_non_ppr.pdf`.

## Preview the year

For 2027, run:

```sh
python3 scripts/season_refresh.py --season 2027
```

This is a dry run. Review the ordered stages and prerequisites; it changes
nothing.

## Prepare the artifacts

After the prerequisites are present:

```sh
python3 scripts/season_refresh.py --season 2027 --execute \
  --confirm REFRESH-2027 --archive-confirmed
```

This downloads and rebuilds target-season artifacts, logs each stage, restores
published pointers if a stage fails, and runs the readiness gate. It does not
activate 2027, create its draft database, or connect to Google Sheets.

## Activate only after review

Review `.local/refresh-runs/<season>-<timestamp>/manifest.json` and the
readiness report. Season activation is deliberately separate and is not yet an
automatic operation. Do not edit `config/active-season.json` manually. Use the
guided activation command once it has been implemented and tested; it must
create a distinct database with Sheets disabled before changing the active
configuration.

Until activation succeeds, start the app normally with `npm run dev` to view
the finalized 2026 draft.
