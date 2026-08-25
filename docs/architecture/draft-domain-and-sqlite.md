# Draft Domain and SQLite Contract

## Authority and aggregates

SQLite is authoritative during a draft. The `draft` aggregate owns the ordered
event sequence and current version. Team budget/roster state, player
availability, the active nomination, and completed sales are updated in the
same local transaction as the corresponding immutable event. Remote sync is
never part of that transaction.

Primary aggregates are:

- **Draft:** configuration, lifecycle, monotonic state version, and event order.
- **Team:** owner, starting budget, remaining budget, and roster slots.
- **Player pool:** availability plus immutable imported model provenance.
- **Nomination:** at most one open nomination per draft.
- **Sale:** final winner and price only; there is no bid stream.
- **Sync outbox:** retryable projections of committed local events to Sheets.
- **Decision planning:** immutable decision snapshots, per-nomination committed
  ceilings, and recorded discipline overrides.

## Commands and events

The application accepts explicit commands such as `OpenNomination`,
`CancelNomination`, `RecordSale`, `VoidSale`, `ReassignRosterSlot`, and
`CompleteDraft`. Every command carries an idempotency key and expected draft
version. A successful command must, in one SQLite transaction:

1. validate the expected version and all domain invariants;
2. append exactly one immutable `draft_events` record;
3. update materialized state tables;
4. advance the draft/team versions; and
5. enqueue an idempotent `sync_outbox` operation.

Commit locally before attempting network work. A repeated idempotency key
returns the prior result. A stale expected version fails without mutation.

## Sale invariants

`RecordSale` must verify:

- the draft is active and the nomination is open;
- the nominated player is available and has no active sale;
- winner, nomination, and player belong to the same draft;
- price is at least the minimum bid and no more than remaining budget;
- after purchase, remaining budget can still cover every open slot at $1;
- an eligible open roster slot exists; and
- the state version has not changed.
- purchases above the Renegades walk-away price are recorded for review
  but are not rejected; only the legal budget and roster rules are hard stops.

The transaction closes the nomination, creates the sale, fills a roster slot,
marks the player sold, decrements budget/open slots, appends the event, and
queues synchronization. Cross-table invariants belong in deterministic domain
code and transaction tests; SQLite constraints provide the final defensive
boundary.

## Corrections and audit

Events are update/delete protected. Corrections append compensating events.
`VoidSale` marks the sale void, reopens the roster slot, restores budget and
availability, and records why. A corrected sale is a new nomination/sale event,
not an edit of history. No user-entered event is silently discarded.

## Recovery

On startup, enable foreign keys, WAL, and full synchronous durability. Load the
materialized state and verify its version against the last event sequence.
When inconsistent, rebuild materialized draft state by replaying events into a
fresh transaction and compare the result before replacing caches. Pending and
failed outbox rows survive restart and retry without blocking draft actions.

## Model imports

`artifact_imports` records schema version, build ID, path, checksum, and
metadata. `draft_player_pool` references the exact market, production, and
owner-profile artifacts imported before draft night. Refreshes create a new
artifact record; they never silently rewrite provenance for an active draft.

## Migration

The executable initial schema is `db/migrations/001_initial.sql`; decision
planning is added by `db/migrations/004_decision_planning.sql`. Migrations
are append-only and run in order against a backup. Application startup must not
perform an irreversible migration without first verifying a recoverable copy.

## Implemented service

`src/domain/DraftService.ts` implements transactional initialization, draft
start, nomination open/cancel, sale recording, sale reversal, version checks,
idempotency, local event/outbox writes, and recovery audits. It contains no
network dependency. `src/domain/importDraftArtifacts.ts` initializes the 2026
pool, ten owners, fourteen roster slots per team, model values, risk flags, and
artifact provenance from the current generated JSON artifacts.

Run `npm run typecheck` and `npm run test:domain`. The guarded full rebuild also
runs both checks before publication.
