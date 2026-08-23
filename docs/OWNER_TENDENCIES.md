# JUGG Owner Tendency Profiles

## Scope

Profiles use 840 completed purchases from 2020–2025: six complete drafts, 84
purchases, and 14 roster slots for each of ten stable owners. Evidence strength
is high for broad construction and positional behavior. These signals are
probabilistic context and must not be treated as owner intent.

Purchase order is unavailable. The profiles therefore make no claims about
nomination strategy, early/late spending, budget at time of purchase, or bid
behavior.

## Metrics

Each profile contains:

- average spend, unused budget, maximum purchase, $30+ players, and $1 players;
- top-three purchase concentration and a balanced/mixed/stars-and-scrubs label;
- positional counts, spending shares, league-relative deviations, and
  year-to-year directional consistency;
- salary minus ESPN auction value as an external market-relative comparison;
- repeat-player history; and
- NFL-team preferences using empirical-Bayes shrinkage toward league rates.

A position is labeled overweighted or underweighted only when its spend-share
deviation is at least three percentage points and the direction appears in at
least half of seasons. Team preferences require at least four purchases and a
shrunken lift of 1.25 or greater. Market-relative ESPN residuals are descriptive
comparisons, not causal owner effects or substitutes for the JUGG price model.

## Runtime use

Initial owner signals should be shown as supporting evidence: likely positional
competition, construction style, repeat-player affinity, and weak team affinity.
They should not directly change production value. Any adjustment to expected
sale price must first demonstrate forward-held-out improvement over the current
owner-agnostic price model.

Run `python3 scripts/owner_tendencies.py` directly, or use the guarded full
workflow `python3 scripts/rebuild_all.py`. Current JSON and CSV artifacts are
referenced by `data/processed/owner_tendencies/latest.json`. Each build also
includes `owner_profiles.md`, a readable owner-by-owner interpretation report
generated from the same validated profile data. The report opens with a league
summary table and threshold-based strong-signal bullets, followed by the full
owner writeups. Strong signals are separated into stylistic positional trends
and personnel-specific repeat-player or NFL-team trends.
