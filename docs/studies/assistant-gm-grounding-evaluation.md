# Assistant GM Grounding Evaluation

## Review scope

This is the implementation review gate, not approval for a live mock draft.
Evaluation used deterministic in-memory packets, the mock provider, and a
temporary isolated SQLite database. It did not use `.local/renegade-draft-room.sqlite`,
Google Sheets, model builds, or artifact pointers.

## Fixtures

Development cases cover an expensive elite player with a $35 Walk-Away, a $24
recorded fallback, seven-of-nine support, owner evidence, budget pressure, and
malicious strategy notes. Service cases cover success, cancellation, provider
failure, timeout, a draft action during generation, audit persistence, and a
sale after AI failure.

Final-review case categories are kept conceptually separate from prompt-writing
examples: expensive star; low-cost depth; no fallback; thin tier; constrained
budget; conflicting or absent owner evidence; bye-week concern; and a sale
above Walk-Away. The current automated fixture directly grades the first,
thin-tier/fallback, budget, owner uncertainty, prompt injection, and failure
families. No-fallback, low-cost depth, bye-week, and above-Walk-Away behavior
are covered by the deterministic suite and packet contract; a live-model prose
grade remains pending until a provider is configured.

## Results

- TypeScript strict checking passed.
- All 34 domain tests passed, including five Assistant GM tests.
- Packet version, authoritative state version, five bands, Walk-Away,
  alternative, preferences-as-untrusted-data, and correction/reset/sale trigger
  construction passed.
- Mock streaming, cancellation, timeout, provider failure, stale-response
  rejection, append-only audit, and no draft-event mutation passed.
- Action-oriented mock output names the supported price boundary and recorded
  alternatives; post-sale output lists up to three top Upcoming Targets with
  deterministic target prices, Walk-Aways, conditional plans, and fallbacks.
  When the Renegades are next in the saved rotation, they are framed as
  nomination options rather than a single prescribed choice.
- Pre-nomination context uses `null` rather than fabricated `$0–$0` price bands;
  responses use known roster, market, scarcity, and alternative evidence without
  volunteering that the ladder is absent.
- Invented `$999` and literal title-probability language were rejected.
- A sale remained successful after provider failure.
- The existing deterministic tests continued to pass for legal accounting,
  recovery, monotonic ladders, sold/no fallback, thin tiers, and Walk-Away
  boundaries.

The mock response is effectively immediate; the route streams in short chunks.
Live-provider latency and cost are unknown until a model is configured and
measured. Input is bounded by the validated packet and a 1,000-character
question; live-provider output is capped at 500 tokens and instructed to stay
usually within two to four conversational sentences and about 120 words. Up to
eight bounded, untrusted recent conversation turns may also be included for
follow-up continuity. Privacy exposure is limited to the explicit packet sent when a remote
provider is enabled. Offline cost is zero.

## Limitations and decision

Grounding validation is deliberately conservative but not semantic proof: it
checks the structured contract, dollar claims, shadow-probability wording,
state freshness, and nomination set. A fluent response could still misstate a
relationship between valid facts. Owner evidence is sparse; player news and
injuries are unavailable unless already represented as risk flags. Unsupported
questions must be answered as missing context.

The implementation is safe to inspect with the mock provider. Enabling a live
provider for a mock draft is **not yet approved** at this stop point: George
must choose/configure the server-side provider and review these results and UI.
