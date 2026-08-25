# Renegade Draft Room — Hardening Guide

## Current state in one sentence

The full draft-night workflow and deterministic recommendation packet have
passed isolated full-draft, edge, and recovery testing. Historical chronology
and calibrated championship probabilities remain unavailable, so those claims
must stay narrower than the operational readiness claim.

## What is already in good shape

- **Offline draft operation:** nominations, sales, corrections, rosters,
  budgets, and recommendations are saved locally.
- **Clear data roles:** projections, actual stats, ADP, public auction values,
  JUGG prices, and production values remain distinguishable.
- **League-specific price modeling:** the price model was tested forward in
  time rather than graded on data it had already seen.
- **Player details:** actual/projected stat tables, position rank, replacement
  value, and both tier systems are available in the application.
- **Decision discipline:** walk-away checkpoints, consequence warnings,
  optional revision notes, snapshots, and What Changed explanations reduce emotional drift.
- **Adaptive planning:** Upcoming Targets recalculates from current players,
  rosters, budgets, tiers, replacement paths, and personal strategy.
- **Recovery design:** local state is authoritative; Google Sheets and future
  AI services cannot block essential draft actions.

## What is useful but should be treated cautiously

| Area | How to use it today | Why caution remains |
| --- | --- | --- |
| Expected JUGG price | Strong starting estimate | Historical error is still several dollars and unusual room behavior can move prices |
| Price ranges | Planning band, not a promise | Range calibration is still preliminary |
| Live market adjustment | Directional room signal | Early sales are a small sample, so adjustment is intentionally restrained |
| Production value and tiers | Compare players and replacement paths | They depend on preseason projections and replacement assumptions |
| Championship advice | Secondary shadow signal | Historical projection-to-outcome separation is weak |
| Owner tendencies | Helpful context | Six drafts are not enough to treat behavior as certain |
| Upcoming Targets | A disciplined short list | It is a roadmap heuristic, not yet a fully calibrated autopilot |
| AI | Future explanation layer | A deeper live AI service is not connected yet |

## Value-metric simplification

### The overlap problem

Several current fields are different views of the same underlying facts:

- projected points, position rank, production tier, points above replacement,
  and production dollars all begin with the same projection;
- pre-draft price, live price, price range, auction tier, ESPN value, and ADP
  all describe market cost or market attention;
- production value, Renegades value, edge, live edge, recommended range, and
  walk-away price all look like dollar “values,” even though they serve
  different purposes;
- projected lineup points, championship equity, equity delta, recommendation
  band, and scenario support are all views of roster-outcome testing.

Showing all of them as equal headline metrics would create false complexity and
make contradictions hard to interpret.

### Recommended five-metric core

| Core metric | Keep it because | What it replaces or absorbs |
| --- | --- | --- |
| **1. Live expected price + range** | Best estimate of what the room will charge | Pre-draft price remains a reference; auction tier, ESPN value, ADP, and prior price become supporting evidence |
| **2. Points above replacement** | Measures the production we would lose by waiting too long | Projected points and position rank remain descriptive; production dollars become an internal conversion rather than a headline |
| **3. Scarcity/fallback summary** | Says whether similar production can be bought later and for how much | Production tier, tier remaining, tier drop, replacement player, and replacement cost combine into one decision signal |
| **4. Buy-versus-pass outcome + support** | Directly tests the effect on attainable roster paths and how consistently scenarios agree | Raw lineup score, precise championship equity, equity delta, and recommendation band become views of one outcome family |
| **5. Recommended range/walk-away price** | Converts all evidence into a checkpoint for reassessing a live bid | Renegades value, live edge, and price ladder become explanation or presentation around that checkpoint |

This is the permanent decision hierarchy: core metrics drive recommendations
and receive primary visual emphasis; supplemental metrics explain inputs,
assumptions, and uncertainty in a secondary visual treatment. Adding a new
metric requires assigning it to one of those roles. A new headline metric
should be rejected when it merely restates an existing core family.

### Keep as supporting information

- **Projected points and stat lines:** essential evidence, but not another
  auction value.
- **Position rank:** useful for quick orientation, especially in roster views.
- **Production tier:** important inside the scarcity summary.
- **Pre-draft expected price:** useful for showing how the room has changed.
- **Production value:** useful internally and for backtesting surplus.
- **Edge:** useful as a compact player-list scan, but it is only production
  value minus price and should not drive the final recommendation alone.
- **ADP and ESPN value:** model inputs and comparison references, not answers.
- **Draft probability:** useful before the draft for pool coverage and the risk
  that a player goes undrafted; weak as a live purchase metric.
- **Owner tendencies and personal preferences:** contextual modifiers that must
  show their evidence or exact adjustment.

### De-emphasize or hide from the main decision view

- **Renegades/strategy value as a separate headline dollar amount.** It largely
  duplicates production value plus a preference adjustment. Show the
  adjustment and reason beside the walk-away price instead.
- **Both edge and live edge at once.** Keep live edge in the scanning table and
  expose the frozen comparison only in details or audit views.
- **Auction tier as a major recommendation metric.** It is a convenient summary
  of expected prices, but expected price and range are more actionable.
- **Exact championship percentages during the draft.** Until calibration
  improves, emphasize direction, range, and scenario support.
- **Surplus rank.** It is a ranking of the already-derived edge and adds little
  beyond sorting by edge.

### Shared walk-away decision

The system now uses the live roster-completion price curve as the shared
actionable checkpoint for official nominations, Upcoming Targets, plan edge,
and the initial walk-away price. The policy combines:

1. market price and uncertainty;
2. buy-versus-pass roster outcome;
3. replacement scarcity and opportunity cost;
4. hard budget/roster limits; and
5. small, visible personal adjustments.

Production value and production surplus now help explain and test that policy;
they no longer independently set a competing live action price. The contract
has passed generated-order historical-price stress tests and focused decision
edges. Exact historical decision-policy replay remains impossible without
nomination chronology and losing bids.

### What deterministic logic and AI each need

The deterministic engine needs structured numbers and hard rules: price range,
roster/budget state, production above replacement, tier/fallback information,
scenario outcomes, uncertainty, and bounded preferences. It owns availability,
legal bids, roster construction, recommendation bands, and ceilings.

AI needs that same compact packet plus actual/projected stat lines, source
labels, risk flags, owner evidence, and confirmed room notes. It should explain
why signals agree or conflict, identify missing context, and propose a reasoned
exception. It should not receive ten unlabeled value fields and choose whichever
supports the most persuasive story.

## Highest-value hardening work

### 1. Extend historical replay evidence

Current-compatible actual prices and buyers now run through carefully labeled
generated orders. If nomination chronology or losing bids become available,
add them rather than treating the current stress test as exact replay.

Success looks like:

- legal rosters and correct budgets after every pick;
- stable recommendations after refresh or restart;
- fewer obvious overpays and fewer missed replacement cliffs; and
- a measurable comparison against simple baselines such as ADP or ESPN value.

### 2. Calibrate advice, not just predictions

We have tested price prediction and parts of the outcome model. We should also
grade the actual decision policy:

- Were walk-away prices too high or too low?
- Did waiting for the fallback usually help?
- Did tier-scarcity alerts fire at the right time?
- Did Upcoming Targets improve the final attainable roster?
- How often did strong advice outperform neutral advice?

This turns a collection of good signals into evidence that the complete
decision system works.

### 3. Strengthen uncertainty

Recommendations should become less confident when inputs are weak. Improve and
test price-range coverage by position and price level, projection disagreement,
rookie uncertainty, injury risk, owner-signal sample size, and championship
simulation noise.

The goal is not more numbers. It is better labels such as **high confidence**,
**fragile because the tier is thin**, or **uncertain because projections
disagree**.

### 4. Audit the data joins

Expand the human-reviewed player-identity sample, especially for name changes,
trades, rookies, defenses, and players absent from one provider. Continue to
show missing data instead of forcing a match.

Also verify before draft night that:

- every likely drafted player has the expected stat and model fields;
- actual and projected seasons are labeled correctly;
- all 140 roster slots can be filled legally; and
- source snapshots and model versions are recorded.

### 5. Run draft-night failure drills

Complete at least one full mock auction while deliberately introducing:

- an internet outage;
- a failed Google Sheets update;
- a browser refresh and application restart;
- a mistaken sale followed by correction; and
- a full reset and recovery from backup.

The draft should remain usable, recover exactly, and never lose an accepted
action.

## Product work that remains

- Connect a grounded AI assistant while keeping the deterministic baseline
  visible and available offline.
- Add **Room Notes** so confirmed observations can inform AI explanations
  without silently changing model facts.
- Expand Upcoming Targets into a read-only full-roster autopilot simulation
  that shows several complete roster paths and their tradeoffs.
- Add clearer confidence and freshness labels throughout the interface.
- Improve owner models if nomination order, bid behavior, or more historical
  evidence becomes available.
- Calibrate active-season replacement and management assumptions using real
  transaction history rather than generic scenarios.

## A practical readiness checklist

Before trusting the app on draft night, confirm:

- [ ] Current projections, actuals, ADP, ESPN values, and JUGG history rebuild
      successfully from the last validated local snapshots.
- [ ] Material player matches and exceptions have been reviewed.
- [x] A complete mock draft finishes with correct rosters, budgets, and history.
- [x] Restart, offline, correction, reset, and Sheets-retry drills pass in isolated state.
- [x] Price ranges and walk-away prices have been reviewed against recent historical
      seasons and simple baselines.
- [ ] Championship advice remains labeled as shadow until its predictive
      separation improves.
- [x] Upcoming Targets and personal preferences behave sensibly in several
      very different draft-room scenarios.
- [ ] The user can complete the full workflow quickly without needing AI or
      entering every bid.

## Recommended focus

The next major feature may be a grounded Assistant GM explanation layer, while
the deterministic packet remains authoritative and fully usable offline.
Continue improving uncertainty and collecting nomination/bid evidence rather
than widening AI authority.
