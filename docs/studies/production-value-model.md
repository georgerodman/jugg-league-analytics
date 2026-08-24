# JUGG Production Value Model

## Purpose

Production value estimates fantasy contribution under JUGG scoring and roster
constraints. It is independent of expected auction price. Their difference is
the expected surplus used to identify potential bargains and overpays.

## Replacement levels and allocation

The initial allocation follows six years of JUGG drafting behavior while
respecting the 140-slot league total:

| Position | Slots |
| --- | ---: |
| QB | 15 |
| RB | 45 |
| WR | 48 |
| TE | 12 |
| K | 10 |
| DEF | 10 |

Replacement points are the projected points of the last allocated player at
each position. Positive points above replacement receive the league's $1,860
discretionary budget proportionally; every one of the 140 modeled roster slots
receives the $1 minimum. Production values therefore sum to $2,000 before
joining to the market-supported player pool.

The 2026 replacement projections are QB 324.987, RB 92.249, WR 101.477, TE
107.060, K 132.620, and DEF 106.650 JUGG points. Kicker and defense values have
lower confidence because their projection inputs are less complete than the
offensive sources.

## Historical bargain backtest

For each 2020–2025 season, preseason production value is calculated without
future outcomes. Projected surplus at sale is preseason production value minus
the actual JUGG salary. Realized surplus is actual nflverse league-scored
production value minus salary.

Across 831 matched sales:

- projected-versus-realized surplus correlation is 0.6573;
- the top projected bargain quartile averaged +$6.835 realized surplus;
- all remaining sales averaged -$6.151; and
- 61.84% of the top bargain quartile finished with positive realized surplus.

This supports the bargain signal as useful, although it does not eliminate
injury, playing-time, projection, or role-change risk.

### Position diagnostics

The bargain signal remains useful when evaluated within positions. Projected
versus realized surplus correlations are 0.422 QB, 0.621 RB, 0.769 WR, 0.809
TE, 0.477 K, and 0.486 DEF. Top-quartile RB bargains realized +$7.251 on
average versus -$7.011 for other RBs; top-quartile WR bargains realized +$6.308
versus -$8.013 for other WRs. Kicker bargain ordering did not improve realized
surplus and must remain low confidence.

## Hardening and sensitivity

The 2026 board is recalculated under the base allocation plus the observed
2025, RB-heavy 2021, and QB-heavy 2020 allocations. It reports each player's
minimum and maximum production value across those variants and flags spreads
of $3 or more. The RB-heavy top-bargain result persists: all top 20 base-model
bargains remain RBs under the audit, while the historical RB backtest is
strong. This supports retaining the result rather than manually suppressing it.

The hardened board flags allocation sensitivity, replacement-boundary players,
wide market ranges, low draft probability, missing core market inputs, and all
K/DEF projection values. These flags qualify recommendations without silently
changing either the market or production estimate.

## Artifacts

Run `python3 scripts/production_value_model.py`. Versioned outputs include the
2026 combined decision board in CSV and JSON plus row-level historical
backtests. `data/processed/production_value_model/latest.json` points to the
current build.
