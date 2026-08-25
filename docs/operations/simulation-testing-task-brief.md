# Renegade Draft Room — Simulation Testing Task Brief

## Objective

Build and run the first repeatable, isolated simulation suite for Renegade
Draft Room. Test whether the complete deterministic decision system produces
legal, stable, sensible auction advice across full drafts—not merely whether
individual functions return expected values.

Stop after the baseline suite, findings report, and recommended fixes. Do not
connect AI or automatically implement material recommendation/model changes
until George reviews the findings.

## Start here

Before making substantial changes, read these files completely:

1. `AGENTS.md`
2. `docs/PROJECT_SPEC.md`
3. `docs/product/hardening-roadmap.md`
4. `docs/product/draft-decision-guide.md`
5. `docs/product/live-market-and-strategy.md`
6. `docs/studies/auction-price-model.md`
7. `docs/studies/production-value-model.md`
8. `docs/studies/championship-equity-method.md`
9. `docs/studies/championship-equity-results.md`
10. `docs/architecture/draft-domain-and-sqlite.md`

Treat `docs/PROJECT_SPEC.md` as the durable source of truth. Call out any
conflict between implementation and documentation.

## Safety and isolation rules

- Do not use or modify the active `.local/renegade-draft-room.sqlite` database.
- Do not reset the active draft.
- Do not write to the connected Google Sheet.
- Do not require network, Google Sheets, or AI availability.
- Run every simulation in a uniquely named temporary SQLite database.
- Disable or replace external synchronization with a recording/failure-test
  adapter.
- Preserve deterministic seeds, configuration, artifact build IDs, and code
  version for every run.
- Do not mutate model input files or advance model pointers merely to make a
  test pass.
- Do not weaken legal roster, budget, reserve, audit, or recovery checks.
- Do not implement bid-by-bid entry. Simulations nominate players and record
  final sales only.

## Important evidence limitation

Historical JUGG sale prices are available, but exact historical nomination
order is not. Clearly distinguish:

- historical prices replayed through simulated nomination orders;
- fully simulated 2026 drafts; and
- designed stress scenarios.

Do not describe simulated nomination sequences as historical replay.

## Phase 1: inspect and design

Map the current deterministic pipeline for:

- nomination;
- sale recording and correction;
- expected and live market price;
- xPAR and named production labels;
- live scarcity and fallback selection;
- Draft Impact;
- price ladder and Walk-Away checkpoint;
- Upcoming Targets;
- owner tendencies and personal strategy;
- roster/budget updates;
- league leaderboard and championship shadow signal; and
- SQLite persistence, recovery, and synchronization outbox behavior.

Design a simulation harness that calls the real domain and decision logic
rather than duplicating formulas in a test-only model. Keep simulation policy
(which player is nominated, who wins, and at what price) separate from the
application logic being evaluated.

Before running a large batch, document:

- simulation inputs and assumptions;
- price sampling method;
- nomination policies;
- owner/winner selection policies;
- deterministic seeds;
- metrics and pass/fail checks; and
- limitations.

## Phase 2: build the isolated harness

The harness must support:

- a new temporary draft initialized from current validated artifacts;
- all 10 owners, $200 budgets, and 14 roster slots;
- editable or generated nomination order;
- final sale recording through the real domain service;
- deterministic price scenarios and seeded random sampling;
- corrections and restart/recovery events;
- complete 140-sale drafts;
- per-action decision snapshots;
- no-op, recording, pending, and failing Sheets adapters; and
- machine-readable outputs for every run.

Capture after every nomination and sale when available:

- authoritative state version;
- nominated player and nominator;
- expected/live price and range;
- xPAR production label;
- scarcity label and comparable alternatives;
- Draft Impact;
- Walk-Away price and five decision bands;
- fallback players and prices;
- Upcoming Targets;
- Renegades roster, budget, open slots, and maximum bid;
- league budgets, needs, and likely competition;
- leaderboard/shadow outcome signal; and
- action latency and any warning or failure.

## Phase 3: baseline scenario suite

Run enough deterministic repetitions to expose instability. Begin with at
least the following scenario families:

### A. Historical-price scenarios

For each 2021–2025 season with compatible players:

- use actual JUGG sale prices where matched;
- generate multiple clearly labeled nomination orders;
- preserve the actual buyer when roster legality permits;
- report unmatched or incompatible records rather than forcing them; and
- compare decisions with simple ESPN-value and ADP baselines.

### B. 2026 market scenarios

Run seeded full drafts under:

1. prices near expected JUGG price;
2. prices sampled within modeled ranges;
3. aggressive/high-price rooms;
4. conservative/low-price rooms;
5. early RB inflation;
6. early WR inflation;
7. elite-player bidding pressure;
8. owners preserving budgets unusually late;
9. owners exhausting budgets early;
10. balanced, top-heavy, and depth-oriented winning rosters; and
11. randomized nomination order and price noise.

Do not hard-code a preferred construction strategy. Let outcomes determine
which approaches perform best.

### C. Designed edge cases

Include:

- the last player in a production tier being sold;
- an advertised fallback being sold before the Renegades can act;
- multiple owners with the same urgent position need;
- a nominated player priced well below and well above the market range;
- a purchase one dollar below, at, and above the Walk-Away checkpoint;
- only one legal roster destination remaining;
- maximum-bid and $1 reserve boundaries;
- late K/DEF and bench completion;
- an owner completing the draft and receiving waiver priority;
- voiding the sale that completed an owner’s roster; and
- no close fallback for a nominated player.

## Phase 4: recommendation audit

Evaluate the decision policy, not only final roster totals.

### Required measures

- Legal-state rate: target 100%.
- Completed-draft rate: target 100% for valid scenarios.
- Exact conservation of league budgets and roster slots.
- Recovery equivalence after restart: state must match exactly.
- Determinism: identical seed and inputs must produce identical results.
- Walk-Away discipline: outcome at prices below, at, and above the checkpoint.
- Price-band monotonicity: advice cannot become more favorable as price rises.
- Fallback validity: advertised alternatives must be available, affordable,
  positionally relevant, and genuinely comparable at the time shown.
- Scarcity-label validity and responsiveness after sales.
- Upcoming Targets attainability and recalculation stability.
- Recommendation churn after small, irrelevant room changes.
- Advice confidence relative to input uncertainty.
- Action latency suitable for a live auction.

### Decision-quality comparisons

Where defensible, compare the Renegades policy against:

- expected-price-only purchasing;
- ESPN-value-only purchasing;
- ADP-priority purchasing;
- production-value/edge-only purchasing;
- a neutral affordable-roster policy; and
- random legal decisions.

Compare final rosters using the existing hierarchy:

- attainable roster production;
- xPAR and replacement exposure;
- lineup strength and depth;
- budget efficiency and stranded money;
- bye-week/risk concentration;
- playoff/championship shadow outcomes; and
- robustness across replacement-access assumptions.

Do not claim calibrated championship probability when the underlying model is
still labeled shadow. Emphasize scenario support, ranges, and relative results.

## Phase 5: reliability drills

Exercise at least one full or partial draft with each condition:

- browser/application restart;
- SQLite service reopen;
- interrupted synchronization;
- Google Sheets unavailable;
- retry after failed synchronization;
- mistaken sale and correction;
- legal roster drag/drop and persisted reassignment;
- active-draft history inspection;
- backup creation and reset in an isolated database only; and
- recovery audit after an intentionally interrupted action boundary.

Essential draft actions must remain available when optional services fail.

## Deliverables

Create:

1. A repeatable single command for the baseline simulation suite.
2. Focused automated tests for invariants and failures found.
3. Versioned machine-readable simulation results.
4. `docs/studies/draft-simulation-baseline.md` containing:
   - plain-language executive summary;
   - exact scope and limitations;
   - scenario table;
   - results and baseline comparisons;
   - strongest and weakest decision behavior;
   - concrete examples of good and bad recommendations;
   - reliability results;
   - prioritized fixes; and
   - whether the deterministic packet is ready for AI explanation.
5. Any repeatable operating instructions under `docs/operations/`.

Update `docs/PROJECT_SPEC.md` only when testing establishes or changes a durable
product/architecture decision.

## Stop and review point

Stop after the first baseline suite and findings report. Present George with:

- what passed;
- what failed;
- whether failures are model, policy, data, UI explanation, or reliability
  problems;
- the highest-risk examples;
- recommended fixes in priority order;
- which fixes require rerunning simulations; and
- a recommendation on whether the system is ready to connect the AI Assistant
  GM.

Do not automatically connect AI. Do not silently tune the policy against the
same scenarios used to report final performance. If fixes are approved, keep a
separate evaluation set or rerun with new seeds and clearly label the new
version.

## Definition of done

The task is complete when:

- the suite runs without touching active draft state or Sheets;
- all valid scenarios finish or have explained failures;
- core accounting and persistence invariants are verified;
- recommendation behavior is measured against simple baselines;
- material weaknesses are supported by reproducible examples;
- results and assumptions are documented plainly; and
- George has a clear review checkpoint before model tuning or AI integration.
