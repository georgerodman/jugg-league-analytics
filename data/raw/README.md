# Raw data

Files in this directory are immutable source snapshots. Cleaning and identifier
normalization must write new files rather than changing these inputs.

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

## `fantasypros_actuals/<season>/<timestamp>/`

- Immutable FantasyPros historical standard-scoring player-points responses.
- Used only for offline projection evaluation, not as a draft-night dependency.
- One offensive-position response plus checksum metadata per request.

## `nflverse/<timestamp>/`

- Immutable CSV snapshots downloaded from official nflverse release assets and
  the nflverse schedule repository.
- Includes the player registry and schedules plus season-specific weekly player
  stats, rosters, and team stats.
- `manifest.json` records source URLs, seasons, schemas, record counts, and
  SHA-256 checksums.
- Normalization, identity matching, and league scoring write only to
  `data/processed/nflverse/<timestamp>/`.
