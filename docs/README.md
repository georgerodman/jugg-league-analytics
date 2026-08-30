# Documentation Guide

Start here when returning to the project. The documents are organized by the
question they answer.

## Source of truth

- [Project specification](PROJECT_SPEC.md) — the authoritative product goals,
  architecture decisions, guardrails, and implementation order.

## Product: what the application does and how to use it

- [Simple system overview](product/system-overview.md) — the short, plain-
  language explanation of how data, stats, models, rankings, live state, and
  recommendations fit together.
- [Draft decision guide](product/draft-decision-guide.md) — plain-language
  explanation of the success benchmark, nomination recommendations, price
  tiers, and end-of-draft scorecard.
- [League rules](product/league-rules.md) — confirmed JUGG scoring, roster, and
  playoff format.
- [Live market and strategy](product/live-market-and-strategy.md) — how live
  prices and soft Renegades preferences affect recommendations.
- [Assistant GM voice and behavior](product/assistant-gm-voice-and-behavior.md)
  — editable tone, wording, answer structure, and example responses.

## Architecture: how the system is organized

- [Repository map](architecture/repository-map.md) — where application, model,
  database, documentation, and generated files belong.
- [Draft domain and SQLite](architecture/draft-domain-and-sqlite.md) — local
  draft state, events, persistence, recovery, and database contract.
- [Assistant GM contract](architecture/assistant-gm-contract.md) — validated
  context packet, prompt, response, provider, and grounding boundaries.
- [Data sources and player identity](architecture/data-sources-and-player-identity.md)
  — source authority, provenance, matching, and durable player IDs.

## Operations: how to run and maintain it

- [Start the next season](operations/start-next-season.md) — the short annual
  checklist for prerequisites, dry run, guarded refresh, and activation review.
- [Data-source operations](operations/data-source-operations.md) — refreshing
  sources, adding providers, rebuilding artifacts, auditing changes, and
  recovery behavior.
- [Change and revalidation workflow](operations/change-revalidation.md) — the
  required rebuild, comparison, fresh-seed simulation, and approval gates after
  changing a model, input, data source, league rule, or recommendation policy.
- [Assistant GM setup and recovery](operations/assistant-gm-setup-and-recovery.md)
  — optional server configuration and offline/failure behavior.
- [Repository cleanup and season rollover](operations/repository-cleanup-plan.md)
  — finalized-season preservation, artifact inventory, deletion gates, and the
  staged path to a compact annual repository.
- [Season rollover](operations/season-rollover.md) — active-season
  configuration, safety gates, and the path to a dry-run-first annual setup.

## History: what happened in completed seasons

- [2026 season record](history/2026-season-record.md) — final draft lifecycle,
  accepted modeling decisions, validation evidence, limitations, and pointers
  to the detailed documents preserved at the final Git tag.

## Simple rule for future documents

- User-facing requirement or instruction → `product/`
- Completed-season evidence or decisions → `history/`
- Technical structure or contract → `architecture/`
- Repeatable maintenance procedure → `operations/`
- Durable project-wide decision → update `PROJECT_SPEC.md`
