# Raw data

Files in this directory are immutable source snapshots. Cleaning and identifier
normalization must write new files rather than changing these inputs.

## Repository retention

Keep the snapshot selected by each source's `latest.json` pointer and any older
snapshot explicitly referenced by a retained model artifact, published study,
or reproducibility record. Superseded intermediate captures may be removed from
the repository after confirming that no retained artifact references them.
Removing a snapshot from the repository does not permit changing its contents;
any restored or newly acquired snapshot remains immutable.

## `auction_history.csv`

- Supplied as cleaned `Auction History - Sheet1 (1).csv` on 2026-08-23.
- SHA-256: `0c2fd504bd36bed690978b9c51c086d2286eb0b1f36a8463886e77d724f0b7a3`
- 840 auction-sale records plus one header row.
- Seasons: 2020 through 2025.
- The user removed the noisy 2019 records and standardized fantasy-owner names.

Columns:

| Column | Meaning | Raw representation |
| --- | --- | --- |
| `Season` | NFL/fantasy season | Four-digit year |
| `FF Team` | Winning fantasy team or owner label | Text |
| `Pos` | Player position | `QB`, `RB`, `WR`, `TE`, `K`, or `DEF` |
| `Player` | Player or defense name | Text |
| `Team` | NFL team abbreviation | Text; two blanks |
| `Salary` | Winning auction price | Dollar-prefixed whole number |

Row order must not be interpreted as nomination or purchase order. The file is
primarily sorted by descending salary.

## `ffa/<season>/raw_stats_<season>_wk0.csv`

- User-provided FFA preseason projection snapshots for 2020 through 2026.
- Acquired from FantasyFootballAnalytics.net (FFA;
  `https://fantasyfootballanalytics.net/`).
- `wk0` identifies the preseason snapshot supplied for each season.
- Preserve these files unchanged; projection cleaning and scoring must write to
  a separate processed-data directory.

Checksums and schema observations are recorded in
`docs/PROJECTION_DATA.md`.

## `fantasypros/<season>/<timestamp>/`

- Immutable JSON responses fetched from FantasyPros Public API v2.
- One response per draftable position plus a manifest containing request
  parameters, response counts, source tier metadata, and SHA-256 checksums.
- API credentials are never stored in raw or processed data.

## `fantasypros_adp/<season>/<timestamp>/`

- Immutable FantasyPros half-PPR and PPR ADP pool responses.
- Yahoo ADP is extracted from source ID 236; ESPN ADP from source ID 79.
- These are external snake-draft market markers, not auction-dollar values.

## `espn_cheat_sheets/`

- ESPN non-PPR Salary Cap Value cheat-sheet PDFs for 2020–2026.
- Canonical filename: `espn_salary_cap_values_<season>_non_ppr.pdf`.
- Files remain byte-for-byte unchanged; processed manifests record SHA-256
  checksums.
- Published assumptions are 10 teams and a $200 budget per team. These are
  public ESPN estimates, not JUGG-generated auction values.

## `nflverse/<timestamp>/`

- Immutable CSV snapshots downloaded from official nflverse release assets and
  the nflverse schedule repository.
- Includes the player registry and schedules plus season-specific weekly player
  stats, rosters, and team stats.
- `manifest.json` records source URLs, seasons, schemas, record counts, and
  SHA-256 checksums.
- Normalization, identity matching, and league scoring write only to
  `data/processed/nflverse/<timestamp>/`.

## `nflverse_depth_charts/<season>/<timestamp>/`

- Immutable complete-season depth-chart CSV from the official nflverse release.
- The source contains multiple dated snapshots; normalization selects the newest
  complete 32-team timestamp without discarding the preserved source history.
- `manifest.json` records the URL, schema, record count, SHA-256 checksum, and
  ESPN-via-nflverse CC-BY-SA-4.0 attribution required for 2025 onward.
- Normalized team, player, and fantasy-offense views are published separately
  under `data/processed/nflverse_depth_charts/<season>/<timestamp>/`.
