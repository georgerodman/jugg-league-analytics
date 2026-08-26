# Documentation Guide

Start here when returning to the project. The documents are organized by the
question they answer.

## Source of truth

- [Project specification](PROJECT_SPEC.md) — the authoritative product goals,
  architecture decisions, guardrails, and implementation order.

## Product: what we are building and how to use it

- [Simple system overview](product/system-overview.md) — the short, plain-
  language explanation of how data, stats, models, rankings, live state, and
  recommendations fit together.
- [Hardening guide](product/hardening-roadmap.md) — what is solid, what remains
  provisional, and the highest-value work before draft night.
- [Draft decision guide](product/draft-decision-guide.md) — plain-language
  explanation of the success benchmark, nomination recommendations, price
  tiers, and end-of-draft scorecard.
- [V1 application requirements](product/v1-application-requirements.md) — the
  screens and behavior required in the first Draft Room version.
- [League rules](product/league-rules.md) — confirmed JUGG scoring, roster, and
  playoff format.
- [Live market and strategy](product/live-market-and-strategy.md) — how live
  prices and soft Renegades preferences affect recommendations.
- [Assistant GM voice and behavior](product/assistant-gm-voice-and-behavior.md)
  — editable tone, wording, answer structure, and example responses.
- [Product notes](product/product-notes.md) — ideas and open questions that are
  not yet formal requirements.

## Studies: what we tested and learned

- [Championship-equity method](studies/championship-equity-method.md) — how the
  schedule-neutral championship model works.
- [Championship-equity results](studies/championship-equity-results.md) — current
  findings, model strength, stress tests, and limitations.
- [Auction-price model](studies/auction-price-model.md) — expected JUGG sale
  prices and historical evaluation.
- [Production-value model](studies/production-value-model.md) — projected
  on-field value, replacement level, and positional allocation.
- [Projection evaluation](studies/projection-evaluation.md) — equal-footing
  comparison of projection sources.
- [Projection data](studies/projection-data.md) — provider coverage and field
  definitions.
- [Auction-history profile](studies/auction-history-profile.md) — historical
  auction-data inventory and quality findings.
- [ESPN salary-cap values](studies/espn-salary-cap-values.md) — source context
  and import assumptions.
- [Owner tendencies](studies/owner-tendencies.md) — evidence and plain-language
  profiles for each owner.
- [Deterministic readiness review](studies/deterministic-readiness-review.md) —
  historical-price adapter coverage, edge and recovery results, source
  comparisons, limitations, and the gate for Assistant GM integration.

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

- [Data-source operations](operations/data-source-operations.md) — refreshing
  sources, adding providers, rebuilding artifacts, auditing changes, and
  recovery behavior.
- [Simulation testing task brief](operations/simulation-testing-task-brief.md)
  — isolated full-draft testing scope, scenarios, measures, safety rules, and
  review deliverables for a dedicated testing task.
- [Change and revalidation workflow](operations/change-revalidation.md) — the
  required rebuild, comparison, fresh-seed simulation, and approval gates after
  changing a model, input, data source, league rule, or recommendation policy.
- [Assistant GM implementation brief](operations/assistant-gm-implementation-task-brief.md)
  — the grounding contract, implementation phases, safety rules, tests, and
  review gate for adding the AI explanation layer.
- [Assistant GM setup and recovery](operations/assistant-gm-setup-and-recovery.md)
  — optional server configuration and offline/failure behavior.
- [Assistant GM grounding evaluation](studies/assistant-gm-grounding-evaluation.md)
  — isolated fixtures, results, limitations, and mock-draft review decision.

## Simple rule for future documents

- User-facing requirement or instruction → `product/`
- Experiment, model methodology, or result → `studies/`
- Technical structure or contract → `architecture/`
- Repeatable maintenance procedure → `operations/`
- Durable project-wide decision → update `PROJECT_SPEC.md`
