# Fantasy Football Auction Draft Tool — Project Spec

## Purpose

Build a dependable, offline-first assistant for a live fantasy-football auction draft. It should combine league-specific price history, projected player performance, owner behavior, and current draft conditions to recommend decisions in real time without requiring the user to enter every bid.

This document is the durable source of truth for product scope and architecture. Update it whenever the team makes a material product or technical decision.

## Core Models

### Historical auction-price model

Estimate what each player is likely to cost in this specific league. Train from prior auction results and relevant player, season, league, and market features. Account for inflation, changing budgets or roster rules, positional scarcity, keeper effects when applicable, and uncertainty. Outputs should include an expected sale price or range and enough provenance to explain the important drivers.

### Performance-value model

Estimate each player's fantasy contribution and convert it into draft value under the league's scoring, roster, and replacement-level assumptions. Keep projected performance separate from expected market price so the app can expose bargains, overpays, scarcity, roster fit, and risk rather than collapsing everything into one opaque score.

Use FantasyPros as the primary source for preseason player identity and projected counting statistics. Treat FantasyFootballAnalytics (FFA) and future projection or player-data providers as enrichment sources for uncertainty, kicker detail, injuries, biographical attributes, comparison signals, or missing fields. Preserve every provider independently at the raw-data boundary. Merged model inputs must retain field-level source provenance and apply explicit, tested conflict and fallback rules rather than silently blending or overwriting values.

### Owner tendencies

Learn or encode manager-specific behavior from historical drafts: position and team preferences, typical aggression, willingness to pay, timing, nomination patterns, budget discipline, and other repeatable tendencies. Use owner signals as probabilistic context, not certainty, and show when evidence is weak.

## Live Draft Engine

The live engine maintains the authoritative local draft state:

- teams, roster slots, budgets, and remaining needs;
- available, nominated, sold, and undrafted players;
- completed transactions and nomination history;
- market inflation and remaining positional supply;
- continuously recalculated prices, values, recommendations, and risks.

Every completed sale must update the winning roster and budget, remove the player from the available pool, update league-wide constraints, and trigger recalculation. State transitions should be deterministic, validated, persisted, and recoverable.

## Nominated-Player Workflow

Optimize the main draft screen around one currently nominated player. Show the information needed to decide whether and how far to pursue that player: projected performance, expected price or price range, value surplus, positional context, roster fit, risks, comparable alternatives, and relevant owner signals.

There is intentionally no live bid-entry stream. The user selects or confirms the nominated player, uses the app for decision support while bidding happens elsewhere, then records the final winner and sale price. The app immediately advances state and recommendations.

## AI Copilot

The Copilot has two complementary modes:

- Proactive insights: concise, timely alerts about bargains, overpays, scarcity shifts, budget pressure, roster construction, opponent behavior, nomination strategy, and attractive alternatives.
- Chat: natural-language questions grounded in current local draft state, model outputs, historical evidence, and the user's roster goals.

Copilot advice must be explainable and clearly distinguish facts, model estimates, and judgment. AI availability must never be required for core draft operation; the deterministic engine and locally available recommendations remain usable offline.

## Data and Persistence

### SQLite

SQLite is the operational source of truth during the draft. Persist configuration, imported data, model outputs needed at runtime, current draft state, and an auditable transaction/event history. Write locally before initiating external sync. On restart or refresh, reconstruct the exact draft state and identify any pending synchronization work.

Projection imports must be prepared before draft night. The live application reads the last validated local projection artifact and must not call FantasyPros, FFA, or another projection provider during essential draft operation.

### Google Sheets write-through

Google Sheets provides a familiar shared view and optional downstream reporting. Successful local changes should write through to Sheets when connectivity is available. Synchronization must be retryable and idempotent, with visible pending/error status and a reconciliation path. Sheets must not become a runtime dependency or override newer authoritative local state without an explicit conflict policy.

### Offline-first behavior

Prepare all draft-night data and model artifacts locally in advance. Nomination, sale recording, budget and roster updates, recommendations, and recovery must continue without a network connection. Queue remote writes and replay them safely after reconnection. Avoid draft-night dependencies that require package installation, cloud startup, authentication refresh, or live data fetching.

## Technical Stack

- Live application: Next.js with TypeScript.
- Static modeling and data preparation: Python.
- Local persistence and recovery: SQLite.
- Shared/reporting integration: Google Sheets through an isolated synchronization adapter.
- Development environment: a dev container for reproducible setup and tooling.
- Draft-night runtime: a simple local launch path with minimal moving parts; it must not require the user to operate the dev container.

The TypeScript and Python sides should exchange versioned, validated artifacts or data contracts. Model training is static/offline work; live recalculation should use prepared outputs and fast deterministic logic appropriate for an auction clock.

## Success Benchmark

The product succeeds when a user can run an entire real auction draft confidently from one local app: recover from a restart without losing a completed action, continue through an internet outage, record a nomination and final sale quickly, see correct budgets and rosters immediately, and receive useful league-specific recommendations fast enough to influence the next decision.

Before draft night, verify this with a full replay or simulation of a historical draft, including forced network loss, interrupted Sheets synchronization, application restart, and restoration from persisted state. The final state and transaction history must remain correct, and the user must never need live bid-by-bid entry.

## Order of Operations

1. Capture league rules, roster constraints, scoring, budgets, historical auction results, owner identities, and source-data contracts.
2. Build reproducible Python ingestion and cleaning pipelines; use FantasyPros as the primary projection and player-identity backbone, enrich it from source-isolated FFA and future datasets, and establish stable internal player and owner identifiers.
3. Create baseline performance-value and historical-price models, evaluation metrics, uncertainty outputs, and versioned runtime artifacts.
4. Define the domain model and SQLite schema, including event history, state transitions, migrations, and recovery behavior.
5. Implement and test the deterministic live draft engine: nominations, completed sales, rosters, budgets, availability, inflation, scarcity, and recalculation.
6. Build the focused Next.js draft-night interface around the nominated-player workflow and fast final-sale entry.
7. Add owner-tendency signals and expose their evidence and uncertainty in recommendations.
8. Add Google Sheets write-through, retry queues, status visibility, and reconciliation without weakening local authority.
9. Add proactive Copilot insights and grounded chat on top of stable local state and explainable model outputs.
10. Package a reproducible dev container and a separate simple local draft-night launch path.
11. Run historical replays, end-to-end draft simulations, offline and restart drills, performance checks, and a final draft-night readiness test.

## Non-Goals and Guardrails

- Do not require live bid-by-bid entry.
- Do not make Google Sheets, an AI service, or any other network service a prerequisite for core operation.
- Do not train heavy models or perform fragile data acquisition during the live draft.
- Do not allow recommendations to mutate authoritative draft state without an explicit user action.
- Do not hide model uncertainty or imply that owner behavior is deterministic.
