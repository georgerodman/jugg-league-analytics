# Auction History Data Profile

## Coverage

The cleaned history contains 1,260 unique season-player sales across nine accepted seasons.
There are no blank prices, invalid prices, zero-dollar prices, or duplicate
player-season records. NFL-team values from the attached legacy PDFs are
deliberately blank; player names, positions, source team labels, seasons, and
salaries are complete.

| Season | Sales | Teams | Total recorded spend |
| ---: | ---: | ---: | ---: |
| 2012 | 140 | 10 | $2,000 |
| 2015 | 140 | 10 | $2,000 |
| 2019 | 140 | 10 | $1,989 |
| 2020 | 140 | 10 | $1,978 |
| 2021 | 140 | 10 | $2,000 |
| 2022 | 140 | 10 | $1,997 |
| 2023 | 140 | 10 | $1,985 |
| 2024 | 140 | 10 | $1,993 |
| 2025 | 140 | 10 | $1,993 |

Position coverage is 146 QB, 409 RB, 421 WR, 103 TE, 90 K, and 91 DEF sales.

## Modeling implications

### Historical row counts match total roster capacity

The cleaned data contains exactly 14 sales per owner in every season, matching
the confirmed total draftable roster capacity. The current roster uses 9
starters and 5 bench spots. The 2020–2024 seasons used 8 starters and 6 bench
spots. The 2025 roster change converted one bench spot into a WR/RB/TE flex. IR
is never a draftable spot.

### Source review excludes three attached seasons

The newly supplied 2019 ESPN roster export supersedes the earlier rejected
2019 data: it has 140 positive-price sales, 14 players per team, and $1,989 in
recorded spend. The attached 2010, 2013, and 2014 Yahoo exports remain excluded.
2010 is $111 short of the league budget, 2013 contains 26 zero-dollar sales and
totals $2,403, and 2014 contains a zero-dollar sale and totals $2,071 (including
one $271 team). Those failures are source-data defects, not model corrections.

The attached 2020 ESPN export duplicates the existing 140 sales and adds no
rows. All attached NFL-team labels are ignored because the later Yahoo printout
shows last-career teams rather than draft-season teams.

### Some teams spent less than $200

Recorded league spend is slightly below $2,000 in 2020 and 2022–2025. This may
represent unused auction dollars or incomplete/adjusted source records. The
history should retain observed prices rather than forcing team totals to $200.

### Owner identities are stable

Owner/team labels are preserved as source evidence. All accepted older
fantasy-team names now resolve through the commissioner-reviewed,
season-specific aliases in `config/owner_aliases.json`; Jordan remains a
separate former-owner identity rather than being merged into a current owner.

### Purchase order is unavailable

The row order is largely descending salary and cannot support nomination-order,
timing, or remaining-budget features. Those features require another source;
the first historical-price baseline should not claim to use them.

## Initial baseline eligibility

The 2020–2025 records remain the model-training cohort because those seasons
have contemporaneous projections, ADP, and public auction inputs. Accepted
2012, 2015, and 2019 sales seed the prior-JUGG-price feature when a player can
be linked unambiguously to the durable registry; unmatched legacy players keep
provider-scoped provisional identities and do not become fabricated matches.
Evaluate predictions with season-based holdouts so records for a single season
never appear in both training and validation sets. Position-demand features
should encode the 2025 starter-composition change explicitly.
