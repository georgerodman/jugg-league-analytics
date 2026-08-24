# Schedule-Neutral Championship Equity Model

## Objective

The Rodman Renegades' north-star objective is to maximize the probability of
winning the JUGG League championship. Auction surplus remains a cost and
opportunity-cost input; it is not the objective and is not a draft grade.

Before the fantasy schedule exists, the model reports **schedule-neutral
championship equity**: the share of simulated balanced schedules and weekly
player outcomes in which a roster wins the league. In-season championship
probability will later condition the same scoring engine on actual standings,
rosters, schedule, injuries, and remaining matchups.

## Confirmed 2026 format

- Ten teams; Weeks 1–15 regular season.
- Four playoff teams, seeded by record and then total points.
- Week 16 semifinals: 1 vs. 4 and 2 vs. 3.
- Week 17 championship; one-week rounds, no byes, no reseeding, no divisions.

## Model layers

1. Reconciled player-week means anchored to the selected preseason full-season
   projection. Opponent strength shapes the curve, weekly means sum to the
   season projection, and bye weeks are zero.
2. Historical nflverse weekly JUGG points estimate missed-game probability and
   active-game volatility separately. Player estimates shrink toward position
   priors when samples are sparse.
3. A legal lineup optimizer calculates starter points, bench contribution,
   positional strength, and Weeks 16–17 strength.
4. Balanced random schedules average away unknown schedule luck.
5. Weekly outcome simulations estimate top-four and championship equity. A
   modest shared NFL-team factor represents correlated teammate outcomes.
6. Incomplete-draft scenarios compare attainable roster completions after
   buying, passing, or nominating a player.

FantasyPros supports weekly NFL projections through `week=N`, but those are
dynamic weekly consensus projections rather than a guaranteed preseason
decomposition of the week-zero season projection. When available, they should
shape the weekly allocation and then be normalized back to the selected season
total.

## Strategy neutrality

The model does not privilege any named draft strategy. Concentrated elite
production, distributed spending, positional timing, depth, ceiling, and
replacement optionality emerge from the attainable roster paths rather than
being selected in advance. Named styles may be used after the fact to describe
results but never enter decision logic.
The model separately reports draft-only, ordinary replacement-access, and
future active-management scenarios. Successful trades are not assumed until
JUGG transaction history supports a calibrated rate.

The conservative replacement-access scenario allows at most four exclusive,
same-position additions per team. Its decision signal is 70% preseason
projection and 30% trailing-three-week realized performance, with a 20%
improvement threshold (5% after two zero weeks). It never sees the current or
future week's result when making a move. This is a scenario assumption, not a
claim about historical JUGG management.

## Incomplete-roster decisions

For each materially draftable player, the standalone completion engine creates
legal 14-player paths under favorable, expected, and adverse market prices. It
searches through lineup strength, price efficiency, and ceiling lenses. These
are optimization lenses, not preferred strategies. During a live draft the
same contract will start from all ten actual partial rosters, remaining budgets,
and available players before computing championship-equity differences.

## Decision bands

Championship-equity deltas map to strong pursue, lean pursue, neutral, lean
pass, or strong pass only when the magnitude clears the measured simulation
noise and the direction agrees across reasonable scenarios. Neutral is the
default. The current calibration uses a 1.4-point equity noise floor; roughly
7,840 simulations per evaluated path are estimated to reduce the observed
maximum seed range toward one percentage point.

## Nomination decisions

When the Renegades control a nomination, candidates are grouped by intent:

- **Acquire:** desirable roster path at a tolerable likely price.
- **Bargain test:** limited room demand creates a credible cheap-win chance.
- **Budget drain:** likely to consume opponents' scarce dollars without
  materially harming Renegades alternatives.
- **Information:** reveals demand or positional allocation before a later
  commitment.
- **Hold:** strategically better nominated later.

Every nomination suggestion must state likely bidders, expected clearing
price/range, accidental-win risk, affected alternatives, budget-pressure
effect, and the buy/pass championship-equity implication. Player and team
preferences are bounded context, never hard rules.

## Review gate

Do not integrate these outputs into Renegade Draft Room until the standalone
weekly projection, lineup, simulation, incomplete-roster, nomination, and
historical calibration artifacts have been reviewed and accepted.
