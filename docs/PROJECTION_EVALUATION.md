# Historical Projection Evaluation

## Decision

Use FantasyPros as the primary preseason projection source. Retain FFA as an
enrichment and comparison source.

## Evaluation design

The evaluation covers the 2020–2025 seasons and compares total-season standard
fantasy points for the same 2,797 offensive player-seasons. Every evaluated row
must be present in:

- the FantasyPros week 0 preseason projections;
- the FFA week 0 preseason projections; and
- the FantasyPros historical actual-points dataset.

FantasyPros projected standard points are used directly. FFA standard points
are reconstructed from its counting stats using common standard rules: four
points per passing touchdown, one per 25 passing yards, minus two per
interception, standard rushing and receiving yardage/touchdowns, and no points
per reception. This is an equal-cohort source comparison, not yet an evaluation
under the JUGG league's five-point passing-touchdown rules.

## Results

| Cohort | FP MAE | FFA MAE | FP RMSE | FFA RMSE |
| --- | ---: | ---: | ---: | ---: |
| All | 30.019 | 32.410 | 45.311 | 47.493 |
| QB | 48.227 | 50.034 | 72.864 | 73.603 |
| RB | 33.458 | 36.507 | 47.682 | 51.481 |
| WR | 27.871 | 30.432 | 37.993 | 40.560 |
| TE | 17.418 | 19.152 | 24.943 | 26.144 |

FantasyPros has lower MAE and RMSE overall and at every offensive position. It
also has lower overall positive bias: 6.125 points versus 9.070 for FFA.

FFA was slightly better in isolated season-level comparisons: its RMSE was
lower in 2022 and both its MAE and RMSE were lower in 2025. That supports using
FFA as an enrichment and validation signal rather than removing it.

## Identity results

Canonical projections use FantasyPros IDs as the provider-backed identity and
an internal identifier shaped as `nfl:gsis:<gsis_id>` when a validated nflverse
identity is available, with `provisional:fantasypros:<fantasypros_id>` as the
explicit fallback. FFA matching
uses normalized name, position, and team evidence with conservative fallbacks.
Exceptions are emitted rather than guessed.

839 of 840 historical auction sales now map to an internal player identity. Two
sales whose players were absent from that season's FantasyPros projection pool
were resolved through the same unique identity in another season. One reviewed
nickname alias is stored in `config/player_aliases.json`; the remaining
unmatched sale stays visible for review rather than being guessed.

## Limitations and next evaluation

- Total-season results penalize injuries and missed games; availability risk is
  part of draft value but should also be analyzed separately.
- Kicker and defense projections are excluded because provider scoring inputs
  differ and FantasyPros omits kicker distance buckets.
- The comparison measures fantasy-point accuracy, not per-stat error or
  uncertainty calibration.
- FFA standard points are reconstructed rather than supplied by FFA.

Before fitting auction values, add games-played/availability views, evaluate
FFA standard deviations for calibration, and calculate JUGG-specific actual
points from historical counting stats when a reliable actual-stat source is
available.
