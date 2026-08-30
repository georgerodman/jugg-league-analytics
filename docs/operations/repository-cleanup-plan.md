# Repository Cleanup and Season Rollover

## Objective

Reduce the active repository to the maintained application, reproducible annual
pipeline, compact runtime inputs, focused tests, and current documentation while
preserving the finalized 2026 draft independently of development artifacts.

Cleanup follows **preserve → prove → consolidate → prune → verify**. Files are
not removed merely because they are old; each deletion must be supported by a
runtime-dependency audit, a rebuild/archive decision, and clean-checkout tests.

## 2026 preservation checkpoint

The finalized draft is archived with:

- a self-contained SQLite backup;
- readable team, roster, sale, and event CSV exports;
- a README with lifecycle metadata;
- a manifest with row counts, file sizes, SHA-256 checksums, and Git context.

Run:

```sh
python3 scripts/archive_finalized_draft.py
```

The default destination is ignored local storage under `.local/archives/`.
Before deleting operational state or old backups, copy the resulting directory
to durable storage outside this repository and verify its checksums there.

The draft archive above preserves the authoritative draft record. Before
retiring completed-season source and model-building data, create a separate
checksummed data archive:

```sh
python3 scripts/archive_season_data.py --season 2026
```

This bundle contains `data/`, `config/`, the pinned data requirements, and an
internal per-file manifest. Copy it outside the repository before applying the
postseason data prune. It is not needed to run the finalized Draft Room; it is
the recovery copy for detailed model reproduction and historical research.

## Deletion gates

No data or implementation area may be removed until all applicable gates pass:

1. The finalized 2026 archive exists in at least two storage locations.
2. `python3 scripts/audit_repository_artifacts.py` reports no missing runtime or
   test artifacts.
3. The application can load the finalized draft and a fresh-season fixture.
4. TypeScript, Python, domain, build, and offline smoke checks pass.
5. A clean checkout can reproduce the same checks without ignored local state.

## Current classification

### Preserve outside the active repository

- finalized 2026 SQLite archive and readable exports;
- immutable source snapshots needed to reproduce published 2026 analysis;
- licensed or private provider PDFs and downloads;
- historically meaningful studies and final model reports that are not active
  product documentation.

### Keep in the active repository

- Next.js application, domain logic, adapters, and migrations;
- league configuration and reviewed identity overrides;
- supported annual acquisition/modeling scripts;
- compact deterministic fixtures and current published runtime bundle;
- focused tests and authoritative documentation.

### Regenerate locally

- `node_modules/`, `.next/`, Python caches, TypeScript build metadata;
- rebuild logs, temporary PDF renders, and simulation scratch output;
- operational SQLite WAL/SHM files and routine duplicate backups after the
  final archive is copied elsewhere.

### Review before pruning

- repeated timestamped raw and processed snapshots;
- one-time research ingestion and language-repair scripts;
- superseded implementation briefs, readiness reports, and product notes;
- historical simulation and championship-equity builds;
- data referenced only through an obsolete `latest.json` pointer or old test.

## Target season boundary

The active application should eventually consume a compact, versioned season
bundle rather than the full modeling workspace. A new-season command should
create a distinct draft ID, season configuration, SQLite state, and Google Sheet
mapping. Finalized seasons remain immutable and disconnected.

## 2026 cleanup checkpoint

Completed after the finalized archive was copied outside the repository:

- pruned 705 superseded processed artifacts and obsolete raw snapshots;
- retained every published runtime, test, and rebuild dependency reported by
  the repository artifact audit;
- reduced the active data tree from approximately 836 MB to 207 MB;
- removed generated PDF renders, build output, caches, duplicate local backups,
  and the repository-local archive copy;
- retained the timestamped final SQLite backup referenced by the finalized
  draft record;
- condensed completed studies and task briefs into
  `docs/history/2026-season-record.md`; and
- retired the one-time 2026 player-research ingestion and rewrite scripts while
  preserving their published summaries for read-only Draft Room use.

After the external season-data archive was confirmed, the postseason data
prune reduced the active data tree again, from 207 MB to approximately 38 MB.
The retained runtime closure is about 13 MB, the checked-in simulation and
identity fixtures are about 5 MB, and the remaining raw files are compact
provider inputs useful for the next annual refresh. Large refetchable nflverse
sources and non-runtime derived reports are available from the external archive
and `draft-2026-final` tag.

`node_modules/` remains an ignored local convenience so the application can
start without reinstalling packages. It is not part of the Git repository and
may be deleted at any time; restore it with `npm install`.

The final generated-cache pass removed `.next/`, TypeScript incremental build
metadata, and Finder metadata after verification. This reduced the working
directory from approximately 647 MB to 511 MB while retaining `node_modules/`
and the finalized local SQLite state for immediate app startup. Next.js and
TypeScript recreate those ignored caches when the app or checks run.

## Verification commands

```sh
python3 scripts/audit_repository_artifacts.py
python3 scripts/prune_processed_artifacts.py          # reviewed dry run
python3 scripts/prune_processed_artifacts.py --apply  # remove superseded builds
python3 scripts/prune_raw_artifact_versions.py        # reviewed dry run
python3 scripts/prune_raw_artifact_versions.py --apply
python3 scripts/prune_postseason_data.py              # archive-gated dry run
python3 scripts/prune_postseason_data.py --apply --archive-confirmed
python3 -m unittest discover -s tests -q
npm run typecheck
npm run test:domain
npm run build
```

After the compact runtime bundle is introduced, these commands must also pass
from a clean checkout with `.local/`, `node_modules/`, and `.next/` absent.
