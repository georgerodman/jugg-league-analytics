# Fantasy Football Auction Draft Tool — Project Spec

## Purpose

Build a dependable, offline-first assistant for a live fantasy-football auction draft. It should combine league-specific price history, projected player performance, owner behavior, and current draft conditions to recommend decisions in real time without requiring the user to enter every bid.

This document is the durable source of truth for product scope and architecture. Update it whenever the team makes a material product or technical decision.

The consolidated source-authority and player-matching contract is documented
in `docs/architecture/data-sources-and-player-identity.md`.

## Core Models

### Historical auction-price model

Predict the expected sale price or price range for each player in the JUGG
auction. Evaluate publicly available auction-dollar values, ADP, projections,
prior league results, positional markets, rule changes, and eventually owner
behavior as competing and complementary inputs. Select features and model
structure through forward-only historical testing rather than assigning any
provider a privileged role in advance. ESPN's published Salary Cap Value is an
external dollar input; the JUGG prediction is a distinct model output and must
not be presented as ESPN's value or as intrinsic player worth. Every external
dollar value must retain its provider, scoring, roster, team-count, budget,
season, and retrieval assumptions. Evaluate the model with season-held-out
backtests, uncertainty outputs, and transparent baselines.

### Performance-value model

Estimate each player's fantasy contribution under the league's scoring and
roster assumptions, then derive a production-based value that remains separate
from the expected JUGG sale-price model. Keep projected performance, public
auction values, external ADP market signals, historical JUGG sale evidence,
expected JUGG price, and production value separately attributable so the app
can identify likely bargains and overpays without collapsing the signals into
one opaque score.

Reconcile conditional sale prices to the fixed $2,000 league economy by
weighting every supported player's price by the separately modeled probability
that he is drafted. Do not force the 140 highest conditional prices to total
$2,000: that incorrectly assumes the identities of all drafted players are
known in advance and historically compresses premium prices. The production
calibration method must win a forward-only tournament with explicit overall,
$50-plus, and $60-plus error diagnostics.

Assign every player two position-local tiers. The **production tier** groups
players with materially similar projected JUGG points; the **auction tier**
groups players with materially similar expected JUGG sale prices. Tier
boundaries are deterministic natural gaps with bounded within-tier spans, not
fixed player counts. Keep the two tier systems separate so the application can
identify comparable production available in a cheaper auction tier. Recalculate
remaining tier supply after every completed sale and expose it to nomination
recommendations and future draft-roadmap planning.

The runtime player contract also carries a normalized prior-season actual stat
line from nflverse and a current-season projected stat line from the canonical
FantasyPros-primary projection artifact. Preserve season, games, fantasy points,
counting statistics, and source. Missing prior-season history is explicit for
rookies and other players without a valid prior NFL record; it must never be
filled by guessing or confused with a projection.

Use FantasyPros as the primary source for the preseason player pool and projected counting statistics. Treat FantasyFootballAnalytics (FFA) and future projection or player-data providers as enrichment sources for uncertainty, kicker detail, injuries, biographical attributes, comparison signals, or missing fields. Preserve every provider independently at the raw-data boundary. Merged model inputs must retain field-level source provenance and apply explicit, tested conflict and fallback rules rather than silently blending or overwriting values.

Use Yahoo and ESPN ADP, acquired through FantasyPros, as historical external market markers. Yahoo ADP comes from the FantasyPros half-PPR ADP source and ESPN ADP from its PPR ADP source; preserve those scoring-context differences. ADP is snake-draft position, not an auction-dollar value.

Use ESPN's published non-PPR Salary Cap Values as a public historical auction-
value input for 2020–2026. Preserve ESPN's stated 10-team, $200-budget context
and keep these values distinct from ADP, projections, JUGG sale history, and the
league's own rules. A source value is evidence, not a JUGG-generated target.

Use nflverse as the primary historical NFL outcomes and identifier-enrichment
source. Preserve nflverse releases as immutable pre-draft snapshots, normalize
them behind a Python adapter, and calculate actual fantasy points from the
league scoring configuration. nflverse actuals evaluate preseason projections
and provide prior-season model features; they do not replace FantasyPros as the
preseason projection backbone. Name-based identity matching must remain
reviewable and must never silently create a permanent player identifier.

Use GSIS-backed internal identifiers (`nfl:gsis:<id>`) as the preferred durable
identity for NFL players and team identifiers (`nfl:def:<team>`) for defenses.
When no validated GSIS mapping exists, retain an explicit provider-scoped
provisional identifier rather than guessing. FantasyPros, FFA, Yahoo, ESPN,
PFR, and PFF IDs are source aliases on that entity, not the entity itself.
Identity promotion requires collision checks, evidence provenance, a shadow
old-to-new mapping, and regression testing against versioned reviewed records.

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

A deliberate full-draft reset is available from the application. It requires
typing `RESET`, checkpoints and preserves the prior SQLite database as a
timestamped local backup, initializes a clean draft, and projects the empty
rosters to Google Sheets. Renegades strategy and player preferences are
preserved by default but can be reset explicitly from the confirmation dialog.

## Nominated-Player Workflow

Optimize the main draft screen around one currently nominated player. Show the information needed to decide whether and how far to pursue that player: projected performance, publicly sourced auction values when available, historical JUGG prices, external ADP, positional context, roster fit, risks, comparable alternatives, and relevant owner signals.

The application is named **Renegade Draft Room** and highlights the operator's
team, **Rodman Renegades**. The V1 visual direction uses a split-focus desktop
layout: a restrained searchable player list on the left and a dedicated live
decision workspace on the right. The current nomination remains compact while
roster fit, recommendation rationale, likely competition, room pressure,
owner signals, and alternatives receive the available decision space.
Completed picks do not consume a permanent bottom strip; the header's Full
History drawer shows every active sale and provides rapid, confirmed
corrections while the immutable audit history remains preserved.

The visual theme is a practical light workspace: white and light-gray surfaces,
blue interaction accents, larger readable typography, restrained borders, and
minimal decoration. Green and red are reserved for positive and negative
decision meaning. Legibility and draft-night scanning speed take priority over
dark-mode atmosphere or decorative styling.

Within the right-hand decision workspace, information is organized in three
horizontal rows: full-width Player Details first, full-width Assistant GM
second, then Team Roster on the lower left and League Details on the lower
right. Player Details owns projected price, all five price bands, comparable
alternatives, the recommendation, and draft actions. Immediately below the
player name it emphasizes five primary decision cards: live expected price and
range, points above replacement, scarcity/fallback, Roster Impact with its
walk-away price, and the five-band price ladder. The fourth card is the current
price verdict and action boundary; the fifth shows one row each for Great,
Good, Neutral, Poor, and Bad price ranges. A quieter supporting
row contains projected points/rank, production-model context, auction context,
ADP, bye week, and data/risk flags. The traditional actual/projected stat table
follows beneath them. Team Roster uses a tall
QB-through-bench table with bye, paid-price, and positional-strength columns,
totals, and remaining max bid. Strength is based on
position rank and projected points above replacement; it is not a retrospective
grade of whether the auction purchase was good or bad. Its team selector can
inspect any owner's roster. Filled players can be dragged between legal lineup
slots (or swapped when both resulting assignments are legal); each change is
saved locally as an auditable roster-reassignment event and then projected to
the matching fixed slot in Google Sheets. League Details owns likely competition,
aligned opponent needs, and supported owner tendencies.

The Scarcity primary card previews the names of its comparable available and
affordable alternatives on hover. Clicking it opens a scan-friendly list of
those players, ordered by projected points, with team, projection, and live
expected price; selecting a name moves Player Details to that player.

Player Details includes blended Yahoo/ESPN ADP. The player list includes bye week and sorts through
clickable, single-line column headers. Position controls include individual
positions, a combined RB/WR view, and a combined RB/WR/TE skill-position view.
The space-efficient player rail always shows sortable projected points, a
named production label derived from xPAR (Elite, Premium, Starter, Depth, or
Replacement),
the frozen pre-draft projected price, live price, and Roster Impact without an
expand/collapse mode. Its divider is draggable, constrained to preserve a usable
minimum width for both panes, and remembers the operator's chosen width locally.
Roster Impact classifies every
available player at his live expected price as Great, Good, Neutral, Poor, or
Bad, with stronger positive and negative visual treatments for rapid scanning.
The matching primary Player Details card is also named Roster Impact. Its supporting sentence uses plain outcome language—such as “buying creates a better projected final roster in 6 of 9 tested draft paths”—rather than the shorthand “6 of 9 support.” It is a deterministic buy-versus-pass roster outcome
across the nine completion paths, incorporating lineup improvement, roster
need, replacement production, tier scarcity, fallback quality, remaining
budget flexibility, opportunity cost, and bounded personal strategy. Hovering
the result explains the price, role, scenario support, and most relevant
context; Player Details repeats that explanation. Once nominated, the fifth
primary card shows how the outcome changes as bidding rises.
The xPAR Player Details tile retains the precise points-above-replacement value
and adds the same named production label as its plain-language interpretation.
The separate Scarcity tile uses live remaining supply: Unique production, Thin
alternatives, Comparable options, or Highly replaceable. Production labels do
not change as players are sold; scarcity labels do.
Auction tier remains available as supporting context in Player Details but is
intentionally omitted from the player list to reduce scanning noise.
Renegades-specific strategy is stored separately from
market and production models. Preferred/avoided players, preferred/avoided NFL
team-position situations, roster construction, risk tolerance, and bye-week
concentration are bounded advisory inputs: they may make a small, visible
adjustment to the shared walk-away price and recommendations but never make a player unavailable or change the market-price
prediction. Completed sales produce a separate, shrinkage-controlled live
market estimate while preserving the frozen pre-draft prediction. The detailed
contract is in `docs/product/live-market-and-strategy.md`.

There is one authoritative actionable player-dollar checkpoint: the **shared
walk-away price**. It is derived from the live buy-versus-pass roster-
completion price curve, constrained by legal budget and roster flexibility,
then modified only by a bounded and visible personal-strategy adjustment. The
official nomination, Upcoming Targets, plan edge, and initial walk-away price
must use this same amount. Production value and production surplus remain
supporting evidence and backtesting measures; they must not independently set a
competing live action price. Plan edge is shared walk-away price minus live expected
price and is shown only where the full decision ceiling has been calculated.

The permanent metric hierarchy has five core decision families: live expected
price/range, points above replacement, scarcity/fallback, buy-versus-pass
outcome with scenario support, and recommended range/walk-away price. These drive
recommendations and receive primary visual emphasis. Projected and actual stat
lines, projected points, position rank, production value/surplus, production
and auction tier details, pre-draft price, ADP, public auction values, bye week,
risk flags, owner context, personal-adjustment details, provenance, freshness,
and uncertainty are supplemental evidence. They explain or qualify the five
core families but must not appear as competing recommendation outputs.

Player selection is only a private preview and must look unmistakably different
from an official nomination. After the user confirms `Nominate`, the nominated
player's decision card and list row switch to a distinct nomination treatment,
including a persistent **Officially nominated** label and a contrasting accent
or background. Text, iconography, or border treatment must accompany color so
the state remains clear for color-vision differences and under draft-night
glance conditions. The nomination treatment remains until the nomination is
cancelled or its final sale is recorded.

There is intentionally no live bid-entry stream. The user selects or confirms the nominated player, uses the app for decision support while bidding happens elsewhere, then records the final winner and sale price. The app immediately advances state and recommendations.

The header exposes an **Upcoming Targets** roadmap, not merely a background
calculation. It ranks the next eight affordable available players from current
roster needs, expected cost, championship-completion scenarios, positional and
tier supply, replacement cost, and bounded personal-strategy adjustments. Each
target shows its intended role, target price, walk-away price, fallback, and
a conditional pivot. It recalculates locally after every authoritative action.

Every authoritative action also persists a compact decision snapshot. When two
snapshots exist, Player Details exposes a deterministic **What changed** banner
that identifies material movement in the top target, championship equity, or
the active walk-away price. An official nomination creates a persisted
model baseline and walk-away price. The operator may deliberately adjust
that checkpoint with an optional note. A proposed Renegades purchase above it
shows the resulting budget, later maximum bid, and newly constrained targets,
but remains allowed when all league rules are satisfied. Purchases above the
checkpoint remain visible in a discipline audit. Only legal budget, reserve,
and roster constraints are hard stops. These controls guide decisions but never
purchase a player or mutate draft state without explicit action.

The walk-away tile is interactive before bidding. Clicking it opens a read-only
impact preview where the operator can enter any possible winning price and see
the resulting budget, later maximum bid, remaining slots, affected Upcoming
Targets, and current fallback. This preview must not nominate, buy, or otherwise
change authoritative draft state.

Nomination order defaults to owner first-name alphabetical order for 2026 and
is editable in the application. The nominated-by control preselects the next
active owner, while allowing a manual correction; rotation continues from the
owner actually recorded. Owners whose fourteen roster slots are filled are
skipped. The event that fills an owner's final slot creates a persisted draft-
completion record. Active completion order determines waiver tiebreaker order
from first finisher (#1) through last finisher (#10); voiding the completing
sale invalidates that completion and recalculates the active order.

## AI Copilot

The Copilot has two complementary modes:

- Proactive insights: concise, timely alerts about bargains, overpays, scarcity shifts, budget pressure, roster construction, opponent behavior, nomination strategy, and attractive alternatives.
- Chat: natural-language questions grounded in current local draft state, model outputs, historical evidence, and the user's roster goals.

Copilot advice must be explainable and clearly distinguish facts, model estimates, and judgment. AI availability must never be required for core draft operation; the deterministic engine and locally available recommendations remain usable offline.

The V1 layout includes the Assistant GM conversation surface before a remote AI
service is required. Its initial answers are deterministic, local, and labeled
as offline guidance. Connecting streaming AI responses is a later layer and
must preserve that offline fallback.

## Data and Persistence

### SQLite

SQLite is the operational source of truth during the draft. Persist configuration, imported data, model outputs needed at runtime, current draft state, and an auditable transaction/event history. Write locally before initiating external sync. On restart or refresh, reconstruct the exact draft state and identify any pending synchronization work.

Use an immutable, per-draft ordered event log plus transactional materialized
state. Every command carries an idempotency key and expected state version. A
successful nomination, sale, correction, roster reassignment, or lifecycle
change must append its event and update local state in one transaction before
creating retryable remote-sync work. Corrections append compensating events;
they never rewrite or delete audit history. The initial domain and schema
contract is documented in `docs/architecture/draft-domain-and-sqlite.md` and implemented by
`db/migrations/001_initial.sql`.

Decision snapshots, nomination ceiling plans, and discipline overrides are
local SQLite records introduced by `db/migrations/004_decision_planning.sql`.
They remain available after refresh or restart and do not depend on AI, Sheets,
or network access.

Projection imports must be prepared before draft night. The live application reads the last validated local projection artifact and must not call FantasyPros, FFA, or another projection provider during essential draft operation.

### Google Sheets write-through

Google Sheets provides a familiar shared view and optional downstream reporting. Successful local changes should write through to Sheets when connectivity is available. Synchronization must be retryable and idempotent, with visible pending/error status and a reconciliation path. Sheets must not become a runtime dependency or override newer authoritative local state without an explicit conflict policy.

For the 2026 draft, completed sales and compensating sale corrections trigger a
full authoritative roster projection to the `2026 Draft Board` workbook's
`Sheet1` tab. Only each owner's Player and Price cells are written; existing
position labels, formatting, remaining-budget formulas, max-bid formulas, and
salary-cap inputs are preserved. The owner/cell contract is versioned in
`config/google_sheets.json`. The local runtime authenticates with a dedicated
service account whose credential file remains outside version control. Failed
writes remain in the SQLite outbox and can be retried without duplicating picks.

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

The product north star is the Rodman Renegades' probability of winning the
league championship. Playoff probability, expected optimal-lineup points,
points above league average, roster ceiling, resilience, and auction surplus
are diagnostic or intermediate measures; none replaces championship equity as
the final objective.

Before the fantasy schedule exists, use schedule-neutral championship equity:
average over balanced simulated schedules, weekly player outcomes, and the
confirmed four-team playoff structure. Keep three scenarios distinct:
drafted-roster/frozen, conservative replacement access, and (once Yahoo
transactions are available) historically calibrated active management. Do not
assume successful trades. During the season, condition the same framework on
actual rosters, standings, schedule, injuries, and remaining matchups.

Draft recommendations must remain construction-neutral. Do not encode or
select a named strategy such as concentrated spending, distributed spending,
or value-first. Generate legal attainable roster completions from the current
state and allow championship outcomes across price, projection, injury,
volatility, and replacement-access scenarios to determine the recommendation.
Named strategies are retrospective descriptions only.

The nomination workflow must present a state-specific price decision ladder
showing where the recommendation crosses strong pursue, lean pursue, neutral,
lean pass, and strong pass. Each threshold must explain which roster paths,
alternatives, or remaining-budget constraints caused the change. The complete
plain-language presentation contract is in `docs/product/draft-decision-guide.md`.
The live ladder evaluates a realistic market-aware price window rather than
extending to the mathematical maximum bid. Prices above the modeled market
range are progressively downgraded for overpay risk and lost roster
flexibility. Until the full championship simulator is calibrated for live
decisions, the interface shows scenario support—not the experimental
completion-path equity span—as its primary confidence signal.

Maintain a live secondary league-outlook view throughout the auction, ranking
all ten partial rosters by the same robust, schedule-neutral championship-
equity benchmark and realistic completion paths. Recalculate it after every
sale; it may live in a drawer, modal, or separate page rather than occupying the
primary nomination workspace. The Renegades' explicit draft target is first
place on this benchmark. Show uncertainty and treat materially overlapping
teams as close rather than manufacturing precision. At draft completion the
same view becomes the final draft scorecard. Decision efficiency and equity
regret remain separate supporting grades and must not alter the common league-
wide roster-strength benchmark.

The draft-night product succeeds operationally when a user can run an entire
real auction confidently from one local app: recover from a restart without
losing a completed action, continue through an internet outage, record a
nomination and final sale quickly, see correct budgets and rosters immediately,
and receive useful league-specific recommendations fast enough to influence the
next decision. Predictive success is evaluated separately through forward-only
historical calibration, uncertainty, and decision-policy replays.

Before draft night, verify this with a full replay or simulation of a historical draft, including forced network loss, interrupted Sheets synchronization, application restart, and restoration from persisted state. The final state and transaction history must remain correct, and the user must never need live bid-by-bid entry.

## Order of Operations

1. Capture league rules, roster constraints, scoring, budgets, historical auction results, owner identities, and source-data contracts.
2. Build reproducible Python ingestion and cleaning pipelines; use FantasyPros as the primary projection backbone, nflverse/GSIS as the preferred player-identity backbone, enrich projections from source-isolated FFA and future datasets, and establish stable internal player and owner identifiers.
3. Create the evidence-selected JUGG sale-price model and the separate performance-value model, with historical market comparisons, evaluation metrics, uncertainty outputs, and versioned runtime artifacts.
4. Define the domain model and SQLite schema, including event history, state transitions, migrations, and recovery behavior.
5. Implement and test the deterministic live draft engine: nominations, completed sales, rosters, budgets, availability, inflation, scarcity, and recalculation.
6. Build the focused Next.js draft-night interface around the nominated-player
   workflow and fast final-sale entry, including unmistakably different preview,
   officially nominated, and sold visual states.
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
