# Championship Equity — Standalone Review Gate

## Status

The standalone hardening pass is complete. Its deterministic completion and
decision-band contract is now integrated into Renegade Draft Room in clearly
labeled **shadow mode** alongside the established market/value guidance. It is
not yet the primary recommendation because historical projection separation
remains too weak for precise live championship-probability claims.

Current artifact pointer: `data/processed/championship_equity/latest.json`.
Decision artifact pointer: `data/processed/championship_decisions/latest.json`.
The versioned rebuild workflow regenerates the standalone artifacts. The live
app consumes prepared projections locally and performs fast, strategy-neutral
completion comparisons without calling Python, AI, or a network service.

## What passed

- 2026 season projections expand to 10,234 player-week rows across Weeks 1–17.
- Every player's weekly means reconcile to the selected season projection.
- Confirmed bye weeks receive zero projected points.
- Opponent strength shapes each weekly curve while preserving its season total.
- Historical nflverse JUGG scoring separates availability from active-game
  volatility and shrinks sparse player histories toward position priors.
- A shared weekly NFL-team environment factor introduces modest teammate
  correlation.
- The lineup optimizer enforces the applicable historical/current QB, RB, WR,
  TE, flex, K, and DEF structure and excludes unused bench points.
- The simulator uses Weeks 1–15, advances four teams by record then points,
  runs 1-vs-4 and 2-vs-3 in Week 16, and crowns a Week 17 champion.
- Simulation invariants preserve exactly four playoff berths and one title per
  season.
- Fixed seeds make artifacts reproducible; each probability now includes a 90%
  Monte Carlo interval.
- Nomination recommendations have a standalone intent contract for acquire,
  bargain test, budget drain, information, and hold.

## Initial calibration result

The model reconstructed all ten historical auction rosters for 2020–2025 and
evaluated 60 owner-seasons. Preseason projected deterministic optimal-lineup
points correlated **0.1462** with realized nflverse optimal-lineup points.

The roster-level correlations by preseason source were FantasyPros **0.1462**,
FFA-with-FantasyPros-fallback **0.1208**, and their simple ensemble **0.1349**.
FantasyPros won this limited comparison, but none is strong enough to deserve
unqualified primary status on predictive merit.

That is weak predictive separation. The current schedule-neutral equity values
are suitable for testing mechanics and sensitivity, not for user-facing claims
that one draft path has a precisely measured championship advantage.

Position-level median active-week coefficients of variation are currently:

| Position | Weekly CV |
| --- | ---: |
| QB | 0.4321 |
| RB | 0.7419 |
| WR | 0.7468 |
| TE | 0.7872 |
| K | 0.4813 |
| DEF | 0.6260 |

## Strategy-neutral construction diagnostic

Named construction styles have been removed from the model and artifacts.
Spending concentration is retained only as a continuous retrospective
diagnostic, divided into quartiles for readability:

| Top-three spending quartile | Mean share | Owner-seasons | Mean realized optimal points | Mean modeled title equity |
| --- | ---: | ---: | ---: | ---: |
| 1 — least concentrated | 55.57% | 15 | 1,446.39 | 11.43% |
| 2 | 63.23% | 15 | 1,356.71 | 9.72% |
| 3 | 68.90% | 15 | 1,424.13 | 10.22% |
| 4 — most concentrated | 77.60% | 15 | 1,348.17 | 8.62% |

This is descriptive, non-causal, and not monotonic. No concentration target or
named strategy enters a completion, simulation, or recommendation.

## Incomplete-roster and decision replay results

The engine generated legal 14-player completions for all 173 materially
draftable 2026 targets in every combination of favorable/expected/adverse
prices and lineup/efficiency/ceiling objectives. These nine paths per target
are neutral searches, not strategy presets.

Because historical auction chronology is unavailable, the buy/pass test is a
price-controlled same-position substitution proxy. Across 835 comparisons its
directional accuracy was **54.49%**. This is weak and supports a broad neutral
band. It must not be described as a true live decision replay.

## Replacement-access result

The no-future-data replacement policy increased realized optimal-lineup points
from **1,393.85** to **1,435.40** per owner-season on average: a mean gain of
**41.55** and median gain of **34.05** across 60 owner-seasons. This confirms
that a frozen drafted roster materially understates attainable season output.
It does not yet represent actual manager behavior; Yahoo transaction history is
required to calibrate acquisition counts, timing, waiver priority, and trades.

Replacement stress testing produced:

| Access scenario | Mean points | Gain over frozen |
| --- | ---: | ---: |
| Frozen | 1,393.85 | 0.00 |
| Limited | 1,425.24 | 31.39 |
| Baseline | 1,435.40 | 41.55 |
| Active | 1,427.91 | 34.06 |

More activity was not automatically better: the active policy sometimes
overreacted to short samples. The model therefore treats replacement access as
an uncertain scenario, not an unconditional bonus.

## Stability and remaining limitations

The historical run now uses 2,500 simulations per season. Five independent
2025 runs of 1,000 simulations produced a mean owner title-equity range of
**2.06 percentage points** and a maximum of **2.8 points**. Scaling that
observed maximum implies approximately **7,840 simulations per evaluated
decision path** to target a one-point maximum range.

The calibrated decision bands are strong pursue, lean pursue, neutral, lean
pass, and strong pass. The current noise floor is **1.4 percentage points**;
strong recommendations require at least a three-point median equity effect,
the robust scenario range to remain on the same side of zero, and at least 80%
scenario agreement. Neutral is the default.

FantasyPros historical preseason weekly projection snapshots are not present,
so opponent-shaped season anchors remain a fallback rather than true archived
weekly consensus. Same-team competition and detailed QB/pass-catcher
correlation require play-level or richer joint residual calibration. Historical
nomination replay cannot be honestly scored until nomination order/nominator
data are available; sale order alone does not reveal nomination intent.

## Review decision

Keep championship equity, buy/pass deltas, and nomination rankings in shadow
mode through a complete mock-draft review. Do not promote them over the existing
recommendation until price ladders, recalculation speed, explanations, and
disagreements have been reviewed. The next data gate is Yahoo transactions and,
if obtainable, historical nominations and archived weekly preseason
projections.
