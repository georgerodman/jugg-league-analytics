# Projection Data Sources

The authoritative cross-source roles and player-identity contract are in
`docs/DATA_SOURCES_AND_PLAYER_IDENTITY.md`. This document records projection
provider schemas, provenance, and inventory details.

## Source roles

FantasyPros is the canonical backbone for the preseason player pool and
counting-stat projections. nflverse/GSIS provides the preferred durable player
identity. FFA is a complementary enrichment source,
especially for uncertainty estimates and kicker distance buckets. Additional
sources may be added behind the same source-specific raw-data boundary. A
source must not silently overwrite another source's fields; merged artifacts
must retain field-level provenance and document conflict rules.

## FFA source and provenance

The user supplied preseason FFA projection snapshots acquired from
FantasyFootballAnalytics.net (FFA; `https://fantasyfootballanalytics.net/`). The
files were added to the project on 2026-08-23. They cover the 2020–2026 seasons
and use the source file convention `raw_stats_<season>_wk0.csv`.

These files are source snapshots, not model outputs. They must remain unchanged
under `data/raw/ffa/<season>/`. Any imputation, player matching, fantasy-point
calculation, filtering, or other transformation must create a versioned file in
a processed-data directory and retain a link back to the source season and row.

## File inventory

| Season | Records | Columns | SHA-256 |
| ---: | ---: | ---: | --- |
| 2020 | 914 | 65 | `ac64292923cac2485c951af19ca66b197fa23a85c79b89c88038775f183e13d0` |
| 2021 | 942 | 65 | `fb982b0d2c11bb607185cd99c1689e91a7efe1d6f303ebe3c95ec2c6358dff68` |
| 2022 | 886 | 65 | `cab13777fc4ba495e16f20b0759be7257ee53cdea63f93297e59353a807fb98f` |
| 2023 | 967 | 63 | `934d269d4d0ff60486319af74360236b9e49f01889b0298b55e64d301b94597d` |
| 2024 | 964 | 63 | `c56c8c4ceba2e785c11dd3b599f18931eae5e22011792000efd25ff67a3790d9` |
| 2025 | 910 | 65 | `25476503dc01dc3e1eac8a709766e1a4d5e06eeb1f2bdc915a42616ddaf5189c` |
| 2026 | 850 | 63 | `a8f0cc0a887148e858b1a8ac20cf41d897bf70d2c591a0c103680dcc639cf984` |

Record counts exclude the header row.

## Schema notes

The files provide weighted projected counting statistics and corresponding
standard deviations for offensive players, kickers, defenses, and individual
defensive players. They also include source player IDs, biographical fields,
NFL team, position, and injury fields.

The schema changes across seasons:

- 2020–2022 and 2025 contain 65 columns, including `rec` and `rec_sd`.
- 2023, 2024, and 2026 contain 63 columns and omit reception projections.
- The league does not use individual defensive players, so `DB`, `DL`, and `LB`
  rows are outside the draft model's scope but remain in the raw snapshots.
- Duplicate or missing source IDs require inspection before IDs can be treated
  as unique player keys. Stable internal player identifiers must be established
  during cleaning.

The missing reception fields do not prevent calculation of this league's
non-PPR fantasy scoring, but they may matter later for risk analysis or external
comparisons. Transformations must tolerate both schema variants explicitly.

## FantasyPros API pipeline

Current preseason consensus projections can also be acquired from the
FantasyPros Public API v2:

```bash
python3 scripts/fantasypros_projections.py --season 2026
```

The API key is read from `FANTASYPROS_API_KEY` in the process environment or
the ignored project `.env` file. The key is never written to an artifact.

The pipeline requests week 0 projections separately for `QB`, `RB`, `WR`,
`TE`, `K`, and `DST`. It validates that every response's declared count equals
the number of returned players before publishing anything. Raw response bodies
and a checksum manifest are preserved under
`data/raw/fantasypros/<season>/<timestamp>/`. Versioned normalized JSON and CSV
artifacts are written under
`data/processed/fantasypros/<season>/<timestamp>/`, with `latest.json` pointing
to the last successful artifact.

FantasyPros `DST` is normalized to the project's `DEF` position. League points
are calculated from the projected counting stats and `config/league.json`.
FantasyPros' own standard, half-PPR, and PPR totals remain in the processed
artifact for comparison and provenance. A later refresh creates a new
timestamped snapshot rather than modifying an earlier one.

The current FantasyPros kicker schema exposes aggregate field goals made and
extra points, but not field-goal distance buckets or misses. Kicker league
points therefore use a conservative three points per made field goal plus one
per extra point and are labeled `conservative_partial`; the unavailable 50+
bonus and miss penalties are not estimated. Other positions are labeled
`calculated`. Defense scoring includes every points-allowed bucket supplied by
the API, along with its available counting statistics.

### Historical FantasyPros inventory

Historical week 0 API snapshots were acquired on 2026-08-23 without replacing
the FFA source files.

| Season | FantasyPros records | Existing draftable records |
| ---: | ---: | ---: |
| 2020 | 990 | 596 |
| 2021 | 611 | 623 |
| 2022 | 640 | 620 |
| 2023 | 782 | 599 |
| 2024 | 662 | 584 |
| 2025 | 830 | 586 |
| 2026 | 602 | 515 |

The FantasyPros schema is consistent across all seven seasons: the same stat
fields appear for each position in every year, receptions are present in all
years, and every row has a FantasyPros player ID. It also supplies projected
points-allowed buckets for defenses. This makes FantasyPros the cleaner
candidate for the canonical historical preseason counting-stat input. Its ID
is retained as a provider alias, not used as the preferred durable internal
identity.

The older FFA snapshots still contain information absent from FantasyPros:
per-stat standard deviations, kicker distance buckets,
biographical and injury fields, and some underlying expert-aggregation detail.
They should be retained as a complementary uncertainty and enrichment source,
not discarded. Before changing the model's canonical input, player matching
and projection accuracy should be evaluated on the overlapping players. Raw
coverage counts alone do not establish which source is more accurate; some
FantasyPros seasons contain a much larger long-tail player pool.

Historical accuracy results and the primary-source decision are recorded in
`docs/PROJECTION_EVALUATION.md`. Operational instructions for refreshes and new
providers are in `docs/DATA_SOURCE_OPERATIONS.md`.

## Yahoo and ESPN ADP market markers

FantasyPros historical ADP responses are preserved separately under
`data/raw/fantasypros_adp/<season>/<timestamp>/`. Normalized platform values are
written under `data/processed/fantasypros_adp/<season>/<timestamp>/` and joined
to canonical players by FantasyPros ID.

- Yahoo ADP uses FantasyPros source ID `236` in the half-PPR ADP pool.
- ESPN ADP uses FantasyPros source ID `79` in the PPR ADP pool.

| Season | Yahoo ADP rows | ESPN ADP rows |
| ---: | ---: | ---: |
| 2020 | 199 | 486 |
| 2021 | 235 | 229 |
| 2022 | 237 | 227 |
| 2023 | 235 | 497 |
| 2024 | 225 | 488 |
| 2025 | 223 | 490 |
| 2026 | 222 | 494 |

The API returns the complete scoring-pool response rather than reliably
honoring a single-source filter. Normalization therefore extracts the named
source from each player's `experts` map. These values are external snake-draft
market markers, not auction values and not interchangeable across scoring
contexts.
