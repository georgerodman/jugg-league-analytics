# Projection Data Source Operations

This runbook governs projection-source onboarding, routine refreshes, rebuilds,
and publication. `docs/PROJECT_SPEC.md` remains authoritative for product and
architecture decisions.

Source responsibilities and the complete identity-matching hierarchy are
defined in `docs/architecture/data-sources-and-player-identity.md`. This document focuses on
how to operate those pipelines.

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

## Single-command derived rebuild

After changing any existing local input, adapter, identity rule, model, or
configuration, run:

```sh
python3 scripts/rebuild_all.py
```

This deliberately does not fetch network sources. It validates the current
local inputs and then rebuilds canonical projections, projection review,
auction identity matches, projection evaluation, auction price and draft
probability models, production values, historical backtests, and the combined
decision board, followed by owner-tendency profiles. It runs the full test suite and verifies the final board before
publishing a successful rebuild manifest.

Every stage writes a log under `data/processed/rebuilds/<timestamp>/`. The
successful manifest records stage results and SHA-256 checksums for every
published pointer. `board_comparison.json` records added/removed players and
the largest changes in price, probability, production value, and surplus.

The command snapshots all processed `latest.json` pointers before starting. If
any stage, test, or integrity check fails, it restores those pointers and writes
`failure.json`; partial timestamped artifacts may remain for diagnosis but are
not published as current. Source acquisition remains an explicit operation so
an incomplete download cannot silently trigger model publication.

When adding a new source, first implement and validate its source-specific
adapter, identity/provenance contract, fixtures, and comparative evaluation as
described below. Then add its normalized pointer to `validate_inputs`, wire it
into the appropriate canonical/model stage, and run the guarded rebuild.

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

## Refresh FantasyPros rankings, injuries, and news

With `FANTASYPROS_API_KEY` available locally, capture the current premium
context snapshot with:

```sh
python3 scripts/fantasypros_context.py --season 2026 --week 1 --news-limit 100
```

The importer preserves raw endpoint responses beneath
`data/raw/fantasypros_context/`, validates declared counts, normalizes a
versioned artifact beneath `data/processed/fantasypros_context/`, and links
rows to stable internal identities through the current FantasyPros crosswalk.
Review the manifest's returned tier, declared record counts, and unmatched
counts after each refresh. Unmatched long-tail NFL records remain in the
normalized dataset even when they are absent from the current draft pool.

This import does not call an AI model. The 2026 player-research synthesis is a
frozen draft artifact: its one-time ingestion, enrichment, and language-repair
scripts were retired after finalization. The Draft Room may continue reading
the published local summaries, but they are not refreshed in place.

If in-season or next-season summaries are needed, create a new dated workflow
with explicit source, freshness, cost, and validation contracts. Do not present
the frozen 2026 writeups as current news.

## Refresh Yahoo and ESPN ADP

Fetch all supported historical/current seasons or a selected season:

```sh
python3 scripts/fantasypros_adp.py
python3 scripts/fantasypros_adp.py --seasons 2026
```

The importer requests the half-PPR and PPR ADP pools at a rate compatible with
the API limit, preserves both complete responses, and extracts Yahoo source ID
`236` and ESPN source ID `79`. Confirm declared/received counts, platform row
counts, and source IDs before rebuilding canonical projections. Do not relabel
the scoring context or interpret ADP as auction dollars.

## Rebuild the JUGG auction-price benchmark

After refreshing canonical projections, ADP, auction-history matches, or ESPN
Salary Cap Values, rebuild the joined historical modeling table and benchmark:

```bash
python3 scripts/auction_price_model.py
```

The command writes immutable artifacts beneath
`data/processed/auction_price_model/<timestamp>/` and advances `latest.json`.
It runs the neutral forward-only model tournament, rebuilds the historical
training table, and writes the current-season conditional JUGG price scores in
CSV and JSON form.

## Import ESPN Salary Cap Value cheat sheets

Place each PDF in `data/raw/espn_cheat_sheets/` as
`espn_salary_cap_values_<season>_non_ppr.pdf`, then run:

```sh
python3 -m pip install -r requirements-data.txt
python3 scripts/espn_salary_cap_values.py
```

The pipeline extracts embedded PDF coordinates, removes exact duplicate
rendered rows, validates row counts and rank uniqueness, and matches identities
against the season canonical pool, cross-season identities, and nflverse/GSIS.
It publishes per-season and combined CSV/JSON artifacts, a manifest, and
`validation_flags.csv`/JSON under `data/processed/espn_salary_cap_values/`.

Review every flag before using a new build. Add only verified, source- and
season-scoped variants to `config/player_aliases.json`. Never overwrite an old
PDF or processed build; add the new sheet and rerun the pipeline so the last
validated `latest.json` remains recoverable.

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
7. Update `docs/architecture/data-sources-and-player-identity.md` and
   `docs/PROJECT_SPEC.md` if source roles or model policy change. Record the
   final evidence in that season's compact history document.

## Historical rebuild and evaluation

After source or matching changes, run:

```sh
python3 scripts/build_canonical_projections.py
python3 scripts/projection_match_report.py
python3 scripts/match_auction_history.py
python3 scripts/evaluate_projection_sources.py
python3 -m unittest discover -s tests -v
```

## Refresh nflverse depth charts

Fetch and normalize the current 2026 depth-chart release with:

```sh
python3 scripts/nflverse_depth_charts.py --season 2026
```

The source release contains many dated snapshots. The importer preserves the
complete CSV and checksum under `data/raw/nflverse_depth_charts/`, validates
the current schema, and publishes only the newest complete 32-team timestamp
under `data/processed/nflverse_depth_charts/`. The normalized artifact retains
the complete chart in `players` and `teams[].depth_chart`, plus display-ready
QB, RB, WR, and TE arrays in `teams[].fantasy_offense`.

Rebuild the normalized artifact without another download with:

```sh
python3 scripts/nflverse_depth_charts.py --season 2026 --no-download
```

Review the snapshot timestamp, 32-team validation, unnamed source rows, and
provisional identity count after every refresh. Rows with GSIS IDs use the
canonical `nfl:gsis:<id>` format. Rows lacking GSIS retain an explicit
`provisional:nflverse-depth:espn:<id>` identity and must not be guessed. For
2025 onward, display or downstream redistribution must credit ESPN via
nflverse under the artifact's recorded CC-BY-SA-4.0 terms.

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

During the preseason, acquire the current roster for identity matching without
requiring an unavailable or incomplete outcomes release:

```sh
python3 scripts/nflverse_pipeline.py \
  --seasons 2020 2021 2022 2023 2024 2025 \
  --identity-seasons 2026
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

Canonical IDs prefer `nfl:gsis:<gsis_id>` and `nfl:def:<team>`. Records without
a validated mapping use `provisional:fantasypros:<id>` and remain eligible for
later promotion through `config/player_identity_overrides.json`. The crosswalk
also publishes `identity_migration_shadow.json`, collision counts, original
match evidence, and a method-precision placeholder that must not be presented
as measured accuracy until enough records have been human-adjudicated.

Run the corroborated registry audit with:

```sh
python3 scripts/audit_player_identity.py
```

`tests/fixtures/player_identity_audit.csv` is a small, versioned provider-ID
corroboration seed. It detects regression but is not yet the recommended
300–500-row human-adjudicated gold set. Expand it across seasons, positions,
match methods, aliases, trades, common names, and provisional records before
using its precision as a production accuracy estimate.

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
