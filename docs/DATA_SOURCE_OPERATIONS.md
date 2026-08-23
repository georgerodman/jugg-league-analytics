# Projection Data Source Operations

This runbook governs projection-source onboarding, routine refreshes, rebuilds,
and publication. `docs/PROJECT_SPEC.md` remains authoritative for product and
architecture decisions.

## Source contract

Every provider has a stable lowercase source key such as `fantasypros` or
`ffa`. Keep raw, processed, and canonical concerns separate:

- `data/raw/<source>/<season>/<snapshot>/` contains immutable provider output.
- `data/processed/<source>/<season>/<snapshot>/` contains source-specific,
  versioned normalization.
- `data/processed/canonical_projections/<season>/<build>/` contains the merged
  model input. FantasyPros is primary; enrichment never silently overwrites a
  populated primary field.
- Each successful source directory has a `latest.json` pointer. Update it only
  after the complete dataset validates and publishes successfully.

Never store credentials in data, manifests, logs, URLs, fixtures, or Git.
Credentials belong in the ignored `.env` file or process environment.

## Refresh FantasyPros projections

1. Confirm `FANTASYPROS_API_KEY` is available locally.
2. Fetch the requested week 0 season snapshot:

   ```sh
   python3 scripts/fantasypros_projections.py --season 2026
   ```

3. Confirm each declared position count equals its received count.
4. Review schema changes, missing fields, duplicate IDs, and scoring-status
   labels. Do not publish a changed schema without updating tests and docs.
5. Rebuild the canonical season:

   ```sh
   python3 scripts/build_canonical_projections.py --seasons 2026
   ```

6. Review `match_exceptions.json` and resolve genuine aliases in
   `config/player_aliases.json`. Do not create aliases merely to increase the
   match percentage.
7. Run the test suite and verify the canonical `latest.json` points to the new
   validated build.

A refresh always creates a new timestamped snapshot. Never edit or replace an
older raw response. Draft-night code continues using the last locally validated
canonical artifact if the provider is unavailable.

Interpret match exceptions carefully: `unmatched` normally means the primary
source contains a player absent from an enrichment source and needs no action.
`ambiguous_name_position` warrants review. Exact duplicate provider rows are
collapsed deterministically and counted in canonical build metadata; distinct
candidates are never selected automatically.

The combined projection match report also flags unmatched rows inside a
position-specific draftable review band (`QB` 20, `RB` 50, `WR` 60, `TE` 20,
`K` 15, `DEF` 15). Review-band flags distinguish potentially meaningful
enrichment gaps from the provider's long tail; they do not remove or downgrade
the FantasyPros primary projection.

## Refresh FFA or another file-delivered source

1. Preserve the supplied file unchanged under
   `data/raw/ffa/<season>/` or the equivalent source-key directory.
2. Record acquisition time, original filename, record count, schema, and
   SHA-256 checksum in source documentation.
3. Compare its schema with the prior snapshot. Handle additions and removals
   explicitly in the source adapter.
4. Rebuild the affected canonical seasons and inspect match exceptions and
   provenance changes.
5. Re-run historical evaluation when projected values, matching rules, or
   scoring transformations change materially.

## Add a new projection or enrichment source

Before implementation, document:

- provider, license/terms, permitted use, retention, and redistribution rules;
- source key, authentication method, quotas, rate limits, pagination, and
  truncation behavior;
- supported seasons, projection types, positions, stable IDs, update cadence,
  and expected schema;
- whether the source is primary, fallback, validation-only, or enrichment;
- which canonical fields it may populate and the conflict rule for each field;
- outage behavior and how the last known-good artifact is retained.

Then:

1. Add a source-specific raw directory and adapter. Never put provider logic in
   the live draft engine.
2. Capture a sanitized fixture and test authentication failures, rate limits,
   malformed data, truncation, duplicates, empty results, schema drift, and
   interrupted publication.
3. Normalize provider identifiers without treating names as permanent IDs.
4. Extend canonical matching conservatively. Put reviewed exceptions in a
   versioned alias file with season scope where necessary.
5. Add field-level provenance. A merged value must identify its provider and
   source snapshot.
6. Compare the provider against actual outcomes on the same player-season
   cohort before changing primary/fallback policy.
7. Update `docs/PROJECTION_DATA.md` and `docs/PROJECT_SPEC.md` if source roles or
   model policy change.

## Historical rebuild and evaluation

After source or matching changes, run:

```sh
python3 scripts/build_canonical_projections.py
python3 scripts/projection_match_report.py
python3 scripts/match_auction_history.py
python3 scripts/evaluate_projection_sources.py
python3 -m unittest discover -s tests -v
```

Historical actual points are refreshed separately because they consume API
quota and should not change during ordinary projection refreshes:

```sh
python3 scripts/fantasypros_actual_points.py
```

Treat evaluation results as evidence, not an automatic promotion mechanism.
Coverage, MAE, RMSE, bias, missingness, uncertainty quality, and licensing all
matter when assigning a source role.

## Refresh nflverse historical data

nflverse is the historical NFL outcomes and identifier-enrichment source. It
is not a live draft dependency and does not overwrite projection fields.

Fetch and build the supported completed seasons:

```sh
python3 scripts/nflverse_pipeline.py --seasons 2020 2021 2022 2023 2024 2025
```

The command downloads players, weekly player stats, season rosters, weekly
team stats, and schedules. It validates required columns before publication,
stores immutable responses and checksums under
`data/raw/nflverse/<snapshot>/`, and publishes normalized data under
`data/processed/nflverse/<snapshot>/`. The raw and processed `latest.json`
pointers change only after a complete successful build.

Rebuild a preserved snapshot without network access:

```sh
python3 scripts/nflverse_pipeline.py --no-download
```

Review `player_identity_crosswalk.json` after every refresh. Exact
name-position-team and unique name-position matches are accepted with explicit
confidence; unmatched players remain exceptions. Names are matching evidence,
not durable identifiers. The crosswalk retains nflverse/GSIS, FantasyPros,
Yahoo, ESPN, PFR, and PFF identifiers when available.

`league_scored_actuals.json` contains regular-season weekly and season totals
calculated from `config/league.json`. Kicker calculations use nflverse distance
and miss buckets. Defense calculations use team defensive statistics and final
schedule scores for the configured points-allowed bucket. This points-allowed
method should be compared with Yahoo's historical scoring exports before it is
treated as an exact platform reconciliation.

Before promoting a new snapshot, inspect its manifest and match exceptions,
then run:

```sh
python3 -m unittest discover -s tests -v
```
