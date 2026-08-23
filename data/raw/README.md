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

## `projections/raw_stats_<season>_wk0.csv`

- User-provided preseason projection snapshots for 2020 through 2026.
- Acquired from FantasyFootballAnalytics.net (`https://fantasyfootballanalytics.net/`).
- `wk0` identifies the preseason snapshot supplied for each season.
- Preserve these files unchanged; projection cleaning and scoring must write to
  a separate processed-data directory.

Checksums and schema observations are recorded in
`docs/PROJECTION_DATA.md`.
