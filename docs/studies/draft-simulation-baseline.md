# Draft Simulation Baseline

## Executive summary

The first isolated baseline completed 21 of 21 simulated full drafts and 2,940
sales without touching the active draft database, Google Sheets, the network,
or AI. Every run finished with 140 filled slots, legal budgets, an internally
consistent event history, and a clean recovery audit after reopening SQLite.

The deterministic recommendation packet is **not ready for AI explanation**.
The suite found a material policy/presentation defect: in 9 of 21 runs, at
least one price ladder became less negative as price rose (for example Strong
Pass at $1–11, Lean Pass at $12–14, then Strong Pass at $15–16). AI would make
that contradiction sound more coherent without fixing it.

This is a review checkpoint, not a tuning pass. No recommendation formula,
model artifact, pointer, AI integration, or active draft state was changed.

## Scope and assumptions

- Build: `3b96126660baf505`.
- Production artifact: `20260825T193216Z`.
- Ten owners, $200 each, fourteen slots each, and a $1 minimum bid.
- Twenty-one deterministic seeds: two simulated nomination orders for each
  2021–2025 label and eleven distinct 2026 room conditions.
- Every nomination and sale used the real TypeScript domain service. Full
  recommendation packets were evaluated for the first twelve and every tenth
  nomination; accounting state and latency were captured for every sale.
- Price ladders, roster completions, Upcoming Targets, Draft Impact, and the
  league leaderboard used the real live decision engine.
- Sync outcomes were local no-op, recording, pending, and failure states. No
  Google API was invoked.

### Important historical limitation

Exact historical nomination order is unavailable. The 2021–2025 runs in this
baseline are simulated nomination sequences and must not be called historical
replays. More importantly, the current harness does not yet adapt the matched
historical sale-price and buyer records into the live 2026 player contract.
Those ten runs therefore test order sensitivity using the current compatible
pool, not the brief's requested actual-price/buyer preservation. This is a
baseline coverage failure and the top simulation-harness follow-up.

## Scenario results

| Family | Runs | Full drafts | Legal | Main result |
| --- | ---: | ---: | ---: | --- |
| 2021–2025 simulated orders | 10 | 10 | 10 | Five random-order runs exposed ladder non-monotonicity; historical price/buyer adapter incomplete |
| 2026 near expected/range | 2 | 2 | 2 | Legal and recoverable; range-noise run exposed ladder non-monotonicity |
| Aggressive/conservative | 2 | 2 | 2 | Legal; conservative run exposed ladder non-monotonicity |
| Early RB/WR and elite pressure | 3 | 3 | 3 | Legal; no fallback-invalid snapshot found |
| Late/early budget behavior | 2 | 2 | 2 | Legal under $1 reserves |
| Depth/randomized | 2 | 2 | 2 | Legal; both exposed or reproduced price-order sensitivity |

## Required-measure results

- Legal-state rate: **100%** (21/21).
- Completed-draft rate: **100%** (21/21).
- Budget and slot conservation: **passed** in every run.
- SQLite reopen/recovery audit: **passed** in every run.
- Determinism: the repeated `2026-near-expected` smoke run reproduced state
  fingerprint `a6f4676965ec6d7b…`.
- Price-band monotonicity: **failed** in 9/21 runs.
- Captured fallback validity: **passed**; every recorded fallback was available,
  affordable, same-position, and in the comparable production tier.
- Median per-action latency: **10.11 ms**. The 95th percentile was **906.67
  ms**, and the maximum was **1,280.38 ms**. The long tail occurs when a full
  decision packet is recalculated and needs live-auction review.
- Sync unavailability: sales continued locally. Failed and pending outbox rows
  survived through completion and reopen.

Walk-Away boundary outcomes, recommendation churn under irrelevant changes,
uncertainty/confidence alignment, full policy-baseline comparisons, and the
complete designed-edge-case matrix were not measured adequately in this first
artifact. Existing domain tests cover reserve rejection, correction,
reassignment, completion/waiver ordering, idempotency, and stale versions, but
that is not equivalent to scenario-level evidence.

## Strongest behavior

The most trustworthy behavior is reliability: all valid drafts completed with
exact local accounting even while synchronization was marked failed or left
pending. Fallback snapshots also remained internally valid in the captured
decision packets. These are reliability and packet-consistency findings, not
proof that the recommended fallback was strategically optimal.

## Weakest behavior and examples

The highest-risk recommendation example is the opening Devaughn Vele ladder in
`historical-2021-random`: Strong Pass from $1–11, Lean Pass from $12–14, then
Strong Pass from $15–16. Cooper Kupp, Denzel Boston, Cade Otton, Chris Rodriguez
Jr., Keon Coleman, Khalil Shakir, and Ryan Flournoy produced related reversals.
The focused policy review confirmed the cause: scenario deltas were clamped to
be non-increasing, but the final band was not. In particular, the later
budget-flexibility branch assigned `lean_pass` directly. At a higher price that
assignment could overwrite an already computed `strong_pass`, making the final
recommendation more favorable even though every underlying scenario delta had
stayed flat or worsened.

The second-highest risk is evidence coverage: the historical family currently
does not use actual historical prices and buyers. Any historical comparison to
ESPN or ADP would therefore be misleading, so no performance claim is made.

## Reliability drills

Passed in existing tests or this suite: SQLite reopen, local operation with
sync failed/pending, retryable outbox preservation, sale correction, legal
roster reassignment, active history persistence, reserve boundaries, owner
completion, and voiding a completing sale.

Not yet demonstrated by this baseline command: isolated backup/reset, an
intentionally interrupted transaction boundary, and application/browser
restart through the UI layer. These are reliability coverage gaps rather than
observed product failures.

## Prioritized fixes for review

1. **Policy:** make the final composed price ladder monotonic after all market
   and flexibility overrides. Add new-seed evaluation; do not tune on these
   reported scenarios alone.
2. **Harness/data:** add the reviewed historical identity adapter, actual sale
   prices, preserved buyers when legal, unmatched counts, and honest ESPN/ADP
   baselines. Rerun all historical families.
3. **Coverage:** implement the full designed-edge matrix, especially the
   below/at/above Walk-Away boundary, last-tier sale, sold fallback, sole legal
   destination, and no-close-fallback cases. Rerun with separate seeds.
4. **Comparison:** add expected-price, ESPN, ADP, production-edge, neutral, and
   random legal policies and compare completed rosters using the documented
   hierarchy. This requires a new evaluation artifact.
5. **Reliability/performance:** add isolated reset/backup and interrupted-action
   drills, then profile the roughly one-second full-packet tail latency.

## Review recommendation

Do not connect the AI Assistant GM yet. First approve fixes 1–3, keep a fresh
evaluation set, and rerun the baseline. AI should remain an explanation layer
only after the deterministic packet is internally monotonic and the historical
and designed-edge evidence requested by the task brief is complete.

## Focused monotonicity repair review

This section records the policy repair requested after baseline build
`3b96126660baf505`. It is a new review point, not a replacement for the original
baseline findings above.

### Policy change

The final composed recommendation is now clamped against the recommendation at
the immediately lower price. If market-range or budget-flexibility composition
would make the higher-price result more favorable, the prior (less favorable)
band is retained. No band thresholds, scenario scores, market ranges,
flexibility cutoffs, player values, or model artifacts changed.

Automated regression coverage now checks the final ladder for every player in
the domain fixture at normal budget flexibility and for every RB, WR, and TE at
a constrained budget. The assertion compares adjacent final displayed bands,
after all policy adjustments have been applied.

### Fresh-seed evaluation

The paired control and repaired runs used a seed offset of 90,000, producing 21
seeds that were not used by baseline build `3b96126660baf505`. Both runs used
the same seeds and production inputs. Neither run advanced the simulation
`latest.json` pointer.

| Result | Fresh pre-fix control | Post-fix |
|---|---:|---:|
| Artifact | `ff0cc3ae80fbb9df` | `f7a07ac6c742c237` |
| Complete and legal drafts | 21/21 | 21/21 |
| Drafts with monotonic ladders | 11/21 | 21/21 |
| Recommendation packets changed | — | 41 |
| Individual price points changed | — | 123 |
| Changes made less favorable | — | 123 |
| Changes made more favorable | — | 0 |
| Walk-Away values changed | — | 0 |

The affected packets all had the same shape as the reported defect: a low-price
`strong_pass` was temporarily overwritten by `lean_pass`. The repair retained
`strong_pass` across that interval. The paired drafts had identical nomination
orders, winners, sale prices, final rosters, and budgets. Fallback validity and
recovery equivalence also remained true in all 21 runs.

### Unintended-effects review and stopping point

No unintended recommendation expansion was observed: the fix never upgraded a
band, changed a Walk-Away value, or altered a simulated draft outcome. The
change is intentionally conservative when an earlier price is already a
stronger pass. AI remained disconnected; model artifacts and pointers, the
active draft database, and Google Sheets were untouched.

**Review point:** approve this monotonicity repair before proceeding to the
separate historical-adapter and designed-edge work listed above.
