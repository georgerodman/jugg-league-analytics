# Deterministic Recommendation Readiness Review

## Plain-language conclusion

The deterministic recommendation packet is ready to serve as the factual
foundation for a bounded Assistant GM explanation layer. That does **not** mean
every recommendation is proven optimal or that the shadow championship signal
is a calibrated title probability. It means the packet is internally
consistent, legal, recoverable, market-aware, and explicit about missing
historical evidence.

AI may explain and question this packet. It must not invent prices, change
bands, mutate draft state, or become required for nominations, sales, budgets,
rosters, corrections, or offline recommendations.

## What changed in this hardening pass

The historical simulation family now uses the matched JUGG auction record:

- actual historical price when that historical player also exists in the
  current validated player pool and the price remains legally payable;
- actual historical buyer when that owner can still legally take the player in
  the generated order;
- an explicit legality substitution when the actual buyer cannot; and
- exact counts for total records, current-pool compatibility, prices replayed,
  buyers preserved, and buyers substituted.

The order is still generated—price-descending or seeded-random—because exact
historical nomination chronology does not exist. Remaining roster slots use
the ordinary simulated 2026 pool. These are historical-price stress scenarios,
not complete historical decision replays.

## Historical coverage

| Season | Historical sales | Compatible actual prices replayed | Actual buyers preserved |
|---|---:|---:|---:|
| 2021 | 140 | 64 | 64 in both generated orders |
| 2022 | 140 | 74 | 74 in both generated orders |
| 2023 | 140 | 92 | 92 in both generated orders |
| 2024 | 140 | 113 | 113 in both generated orders |
| 2025 | 140 | 130 | 125 in price-descending order; 129 in random order |

The six 2025 substitutions were reported rather than forced. They occurred
because the partial current-player replay no longer had a legal roster path for
the historical buyer in that generated sequence.

## Equal-footing market comparison

The historical simulation does not compare 2026 inputs directly with older
prices; that would be misleading. Market-source performance comes from the
accepted forward-held-out 2021–2025 cohort of 700 actual JUGG sales:

| Price method | MAE | RMSE |
|---|---:|---:|
| Full evidence-selected model | $3.152 | $4.613 |
| ADP-only model | $3.373 | $4.808 |
| Yahoo ADP only | $3.516 | $5.007 |
| ESPN ADP only | $3.641 | $5.241 |
| ESPN auction value only | $3.871 | $5.688 |

The full model remains the strongest of these simple comparisons. ESPN is a
useful input, not a privileged anchor. ADP is stronger alone than ESPN auction
value alone, while the combined model performs best.

This comparison validates the market-price input family, not the optimality of
every live buy/pass decision. Without exact historical nominations and
counterfactual bids, there is no honest historical ground truth for “the app
would have won this auction decision.”

## Edge and reliability coverage

Focused automated tests now cover:

- prices one dollar below, at, and above Walk-Away;
- final ladder monotonicity after every adjustment;
- removal and recalculation after an advertised fallback is sold;
- a one-player production tier;
- a nominated player with no same-position fallback;
- complete deterministic packet fields;
- maximum-bid and one-dollar reserve enforcement;
- only one team having an eligible roster destination;
- full transaction rollback after a rejected/interrupted sale boundary;
- sale correction, roster reassignment, owner completion, waiver ordering, and
  reversal of a completing sale;
- local restart/reopen, failed and pending sync outboxes, and recovery audits;
  and
- isolated backup/reset behavior.

## Full-draft evaluation

The final review uses 21 deterministic scenarios with seed offset 130,000,
which was not used by baseline build `3b96126660baf505`. It does not publish a
new `latest.json` pointer. The review artifact is `d2c138616a850d25`.

Final results:

- 21/21 complete drafts and 21/21 legal drafts;
- 21/21 with monotonic final price ladders;
- 21/21 with valid recorded fallback references;
- 21/21 with exact budget and roster-slot conservation; and
- 21/21 with equivalent recovery after reopening each temporary SQLite
  database.

## Remaining limitations

- Exact historical nomination order and losing bids remain unavailable.
- Current-compatible historical replay coverage is lower in older seasons as
  retired players fall outside the 2026 pool.
- A simple source can be compared fairly on held-out price accuracy, but no
  source or recommendation policy can be credited with counterfactual league
  wins from the available auction record alone.
- The championship signal remains a relative shadow ranking, not a calibrated
  probability of winning the league.
- Full-packet tail latency can exceed one second in simulation and should remain
  visible during live UI performance testing.

## Review point

Approve the deterministic packet as the source for Assistant GM explanations,
subject to the restrictions above. Any future change to a model, model input,
data source, identity mapping, league rule, or recommendation policy must follow
`docs/operations/change-revalidation.md` before draft-night release.
