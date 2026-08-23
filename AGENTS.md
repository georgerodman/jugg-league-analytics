# Codex Project Instructions

Before substantial design or implementation work, read `docs/PROJECT_SPEC.md`. Treat it as the durable product and architecture source of truth. If implementation and the spec disagree, call out the conflict and update the spec when a product decision changes.

## Architecture

- Keep the live draft application in Next.js and TypeScript.
- Keep static data preparation, historical analysis, and model-building in Python.
- Use SQLite as the local operational store and recovery source during a draft.
- Isolate Google Sheets synchronization behind a clear adapter; the draft engine must not depend on network availability.
- Keep domain logic—valuations, budgets, rosters, nominations, recommendations, and owner tendencies—separate from UI and external integrations.
- Favor small, composable modules with typed boundaries and explicit data contracts.

## Coding Style

- Use strict TypeScript and validate data at external boundaries.
- Prefer clear names and straightforward control flow over clever abstractions.
- Make calculations deterministic and testable; document assumptions, units, and model inputs.
- Add focused tests for valuation logic, draft-state transitions, persistence, recovery, and synchronization failure modes.
- Keep Python modeling reproducible with pinned dependencies, deterministic seeds where relevant, and versioned inputs/outputs.

## Reliability and Offline Behavior

- Design offline-first: every essential draft-night action must work without internet access.
- Commit local state before attempting remote synchronization.
- Make writes idempotent where practical and preserve an auditable event/history trail.
- Recover cleanly after refresh, process restart, interrupted sync, or loss of connectivity.
- Never let AI or Google Sheets availability block nomination, sale recording, roster/budget updates, or recommendations based on local data.
- Surface stale data, failed syncs, and recovery status clearly; do not silently discard user-entered draft state.

## Working Agreement

- Preserve `docs/PROJECT_SPEC.md` as the shared source of truth and update it alongside material architecture or product changes.
- Do not invent live bid-entry functionality: the workflow records the nominated player and the final sale result only.
- Protect the simple draft-night runtime. Development may use a dev container, but operating the app locally must remain easy and dependable.
- Implement in the order described in the project spec unless a documented dependency justifies changing it.
