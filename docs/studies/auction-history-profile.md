# Auction History Data Profile

## Coverage

The cleaned history contains 840 unique season-player sales across six seasons.
There are no blank prices, invalid prices, zero-dollar prices, or duplicate
player-season records. Two NFL-team values are blank; player names, positions,
owner identities, seasons, and salaries are otherwise complete.

| Season | Sales | Teams | Total recorded spend |
| ---: | ---: | ---: | ---: |
| 2020 | 140 | 10 | $1,978 |
| 2021 | 140 | 10 | $2,000 |
| 2022 | 140 | 10 | $1,997 |
| 2023 | 140 | 10 | $1,985 |
| 2024 | 140 | 10 | $1,993 |
| 2025 | 140 | 10 | $1,993 |

Position coverage is 91 QB, 273 RB, 287 WR, 68 TE, 60 K, and 61 DEF sales.

## Modeling implications

### Historical row counts match total roster capacity

The cleaned data contains exactly 14 sales per owner in every season, matching
the confirmed total draftable roster capacity. The current roster uses 9
starters and 5 bench spots. The 2020–2024 seasons used 8 starters and 6 bench
spots. The 2025 roster change converted one bench spot into a WR/RB/TE flex. IR
is never a draftable spot.

### 2019 was intentionally removed

The user removed 2019 because its prices were noisy and included implausible
$0 values. It is not part of the current modeling source.

### Some teams spent less than $200

Recorded league spend is slightly below $2,000 in 2020 and 2022–2025. This may
represent unused auction dollars or incomplete/adjusted source records. The
history should retain observed prices rather than forcing team totals to $200.

### Owner identities are stable

The cleaned file contains the same ten normalized owner names in all six
seasons, with 84 records per owner. No alias map is currently required.

### Purchase order is unavailable

The row order is largely descending salary and cannot support nomination-order,
timing, or remaining-budget features. Those features require another source;
the first historical-price baseline should not claim to use them.

## Initial baseline eligibility

The 2020–2025 records are structurally eligible for a first price baseline.
Evaluate predictions with season-based holdouts so records for a single season
never appear in both training and validation sets. Position-demand features
should encode the 2025 starter-composition change explicitly.
