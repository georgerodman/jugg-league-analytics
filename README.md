# JUGG League Analytics

For a guided overview of the project documentation, start with
[`docs/README.md`](docs/README.md).

Data-source responsibilities and the player identity/matching process are
documented in `docs/architecture/data-sources-and-player-identity.md`.

The folder hierarchy, naming conventions, and architectural ownership
boundaries are documented in `docs/architecture/repository-map.md`.

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

The first working version of **Renegade Draft Room** is now available locally.

## Run Renegade Draft Room

Install the pinned application packages once, then start the local app:

```sh
npm install
npm run dev
```

Open the local address printed by Next.js (normally
`http://localhost:3000`). The application creates its recoverable SQLite draft
state under the ignored `.local/` directory and imports the current validated
player board and owner profiles the first time it opens.

Before draft night, verify a production build with:

```sh
npm run typecheck
npm run test:domain
npm run build
```

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
league-scored JSON and CSV artifacts. See `docs/studies/projection-data.md` for the
data contract and provenance details.

FantasyPros is the primary projection source. Historical FFA snapshots are
preserved separately under `data/raw/ffa/<season>/` and will enrich the primary
dataset with uncertainty, kicker detail, and other source-specific fields.

Yahoo and ESPN historical ADP market markers can be refreshed with:

```sh
python3 scripts/fantasypros_adp.py
```

The project predicts JUGG auction sale prices and separately estimates
production-based value. Public auction values, ADP, projections, and historical
league evidence remain independently attributable inputs rather than being
presented as intrinsic value.

Rebuild all derived artifacts from the current validated local inputs with:

```sh
python3 scripts/rebuild_all.py
```

The guarded workflow restores the previous published pointers if any stage or
test fails. See `docs/operations/data-source-operations.md` for refresh, new-source, and
publication procedures.

## Refresh historical nflverse data

Build the immutable historical-results, player-identity, and league-scored
actuals artifacts before draft night:

```sh
python3 scripts/nflverse_pipeline.py --seasons 2020 2021 2022 2023 2024 2025
```

The live application never calls nflverse. It consumes only the last validated
local artifacts. See `docs/operations/data-source-operations.md` for refresh, rebuild, and
review instructions.
