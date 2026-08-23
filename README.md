# JUGG League Analytics

A fantasy football analytics, draft preparation, and league management project built for the JUGG League, a long-running private Yahoo Fantasy Football league.

## Project Goals

The goal of this project is to use historical Yahoo Fantasy Football data to better understand league trends and build tools that improve the fantasy football experience for our league.

The project will include:

- Historical matchup and scoring analysis
- All-time team and manager records
- Head-to-head records between managers
- Historical standings and season results
- Draft history and draft performance analysis
- Player and roster analysis
- Transaction and waiver activity
- League scoring and performance trends
- Draft preparation tools
- League management dashboards and tools

## Yahoo Fantasy Sports Data

The project will use the Yahoo Fantasy Sports API to retrieve read-only data from the JUGG League.

Data may include:

- League information and settings
- Teams and managers
- Weekly matchups and scores
- Standings
- Rosters and players
- Draft results
- Transactions
- Historical league seasons

Historical data will be used to analyze trends across multiple seasons and provide context for draft preparation and league management.

## Intended Users

This is a small, non-commercial project intended for personal use and members of the private JUGG fantasy football league.

Yahoo Fantasy Sports data will not be sold or redistributed.

## Status

This project is currently in development.

## Development environment

Development runs in Docker so Python and Node dependencies stay isolated from
the host machine. Docker Desktop is the only host prerequisite.

Start the environment:

```sh
docker compose up --detach --build
```

Open a shell inside it:

```sh
docker compose exec dev bash
```

Stop it without deleting its dependency volumes:

```sh
docker compose down
```

The container currently includes Python 3.12, Node.js 22, npm, Git, and the
SQLite command-line tool. Project packages will be added and pinned separately
when modeling and application work begins. Python's future `.venv` and Node's
future `node_modules` are stored in Docker volumes rather than on the host.

## Refresh current preseason projections

Save the FantasyPros key as `FANTASYPROS_API_KEY` in an ignored `.env` file,
then run:

```sh
python3 scripts/fantasypros_projections.py --season 2026
```

The command preserves immutable raw responses and writes normalized,
league-scored JSON and CSV artifacts. See `docs/PROJECTION_DATA.md` for the
data contract and provenance details.

FantasyPros is the primary projection source. Historical FFA snapshots are
preserved separately under `data/raw/ffa/<season>/` and will enrich the primary
dataset with uncertainty, kicker detail, and other source-specific fields.

## Refresh historical nflverse data

Build the immutable historical-results, player-identity, and league-scored
actuals artifacts before draft night:

```sh
python3 scripts/nflverse_pipeline.py --seasons 2020 2021 2022 2023 2024 2025
```

The live application never calls nflverse. It consumes only the last validated
local artifacts. See `docs/DATA_SOURCE_OPERATIONS.md` for refresh, rebuild, and
review instructions.
