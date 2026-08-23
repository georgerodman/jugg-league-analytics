# JUGG Auction Price Model

## Product contract

The auction-price model predicts the expected JUGG sale price for a player. It
is a market model, not an estimate of the player's intrinsic production value.
No provider or input is privileged in advance. ESPN values, ADP, projections,
historical JUGG evidence, JUGG predictions, and the separate production-value
model must remain visibly distinct and retain their provenance.

## Baseline dataset

The first benchmark covers the 2020–2025 drafts. Its player-season universe is
the union of ESPN's ranked salary-cap pool and every player actually drafted by
JUGG. This preserves undrafted observations and the 20 JUGG sales that were not
present in ESPN's pool.

| Measure | Count |
| --- | ---: |
| Player-seasons | 1,720 |
| JUGG sales | 840 |
| JUGG sales with ESPN values | 820 |
| ESPN-listed but undrafted player-seasons | 880 |
| Drafted JUGG-only exceptions | 20 |

The versioned modeling table also includes ESPN and Yahoo ADP, JUGG-scored
FantasyPros projected points, prior JUGG sale price, position, team, owner, and
source classification when available.

## ESPN-first benchmark

Errors below compare expected price with the final JUGG sale price only for
drafted players having an ESPN value.

| Baseline | MAE | RMSE | Bias |
| --- | ---: | ---: | ---: |
| Raw ESPN value | $4.287 | $6.305 | -$0.262 |
| Globally calibrated ESPN, leave-one-season-out | $4.221 | $6.284 | +$0.076 |
| Position-adjusted ESPN, leave-one-season-out | $3.988 | $5.757 | +$0.054 |

Raw ESPN error has a median absolute value of $3.00; 80% of covered sales are
within $8.00 and 90% within $10.10.

Raw ESPN bias by position reveals the strongest initial JUGG market effects:

| Position | Sales | Bias (ESPN minus JUGG) | MAE |
| --- | ---: | ---: | ---: |
| QB | 91 | -$4.462 | $5.055 |
| RB | 270 | -$1.422 | $4.400 |
| WR | 287 | +$3.021 | $5.167 |
| TE | 68 | -$2.103 | $3.456 |
| K | 53 | -$1.528 | $1.528 |
| DEF | 51 | -$1.333 | $1.333 |

Negative bias means ESPN is lower than JUGG. These results establish ESPN as a
useful baseline and reveal position-specific JUGG effects; they do not assign
ESPN a privileged role. The following tournament tests all available inputs.

## Neutral model tournament

The neutral comparison defines its cohort independently of every candidate
feature: all 700 JUGG sales from 2021–2025. For test season Y, training uses
only seasons earlier than Y. Hyperparameters are selected using the latest
available training season as an inner forward validation set. Every numeric
input receives the same raw, log, square-root, and missing-indicator treatment.
Regularized regression and distance-weighted nearest-neighbor models compete.

| Model/input set | MAE | RMSE |
| --- | ---: | ---: |
| Regularized regression: all inputs | **$3.152** | **$4.613** |
| Regression: all except prior JUGG price | $3.204 | $4.659 |
| Regression: all except projections | $3.285 | $4.798 |
| Regression: ESPN auction value + both ADPs | $3.303 | $4.784 |
| Regression: all except ESPN auction value | $3.318 | $4.714 |
| Regression: both ADPs only | $3.373 | $4.808 |
| Regression: all except ADP | $3.491 | $5.201 |
| Regression: Yahoo ADP only | $3.516 | $5.007 |
| Regression: ESPN ADP only | $3.641 | $5.241 |
| Regression: ESPN auction value only | $3.871 | $5.688 |

The full regularized model ranks first overall and wins four of five individual
test seasons. The model without ESPN auction value wins 2022. Removing ADP
causes the largest tested deterioration (+$0.339 MAE), followed by removing
ESPN auction value (+$0.166), projections (+$0.133), and prior JUGG price
(+$0.052). Yahoo ADP is the strongest single-provider input in this comparison.

This evidence does **not** support treating ESPN auction value as the model's
primary anchor. It supports using ESPN as one useful complementary input in the
current best model, with ADP carrying more incremental value. The conclusion
applies to conditional sale price; drafted probability remains a separate
modeling problem.

## 2026 conditional sale-price scores

The selected full regularized model is retrained on all 840 sales from
2020–2025 and applied to the 2026 player pool. Scoring is limited to players
with a 2026 ESPN Salary Cap Value or Yahoo ADP because deeper canonical players
fall outside the supported historical sale-price population. The resulting 294
players retain every model input and an explicit missing-input list.

Predictions are calibrated to the fixed JUGG auction economy: 140 required
draft slots, a $1 minimum, and $2,000 total league budget. The top 140 unrounded
predictions therefore sum to $2,000. Preliminary ranges use the 80th-percentile
absolute forward-test error for the player's position. These are conditional
sale prices and ranges, not production values or draft probabilities.

The current ranked outputs are `scores_2026.csv` and `scores_2026.json` in the
versioned directory referenced by
`data/processed/auction_price_model/latest.json`.

## Next iteration

1. Fit and backtest drafted-probability separately from conditional sale price.
2. Confirm the small projection and prior-price gains with additional model
   structures and stability checks before retaining them in production.
3. Improve preliminary position-based ranges with price-tier calibration and
   formal coverage evaluation.
4. Revisit model selection as new seasons or market sources become available.

Run `python3 scripts/auction_price_model.py` to rebuild the dataset and report.
The current artifact pointer is
`data/processed/auction_price_model/latest.json`.
