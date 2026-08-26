# Assistant GM Implementation Task Brief

## Objective

Add a grounded, streaming AI Assistant GM to Renegade Draft Room. The AI is an
explanation and conversation layer over the accepted deterministic decision
packet. It must never become a second valuation engine, mutate authoritative
draft state, or block draft-night operation.

Stop at a review point after the grounded implementation, automated tests, and
evaluation report. Do not grant the AI write access or silently tune the
deterministic recommendation policy.

## Start here

Read these files completely before substantial design or implementation:

1. `AGENTS.md`
2. `docs/PROJECT_SPEC.md`
3. `docs/studies/deterministic-readiness-review.md`
4. `docs/operations/change-revalidation.md`
5. `docs/product/draft-decision-guide.md`
6. `docs/product/live-market-and-strategy.md`
7. `docs/product/hardening-roadmap.md`
8. `docs/architecture/draft-domain-and-sqlite.md`
9. `src/domain/liveDecisionEngine.ts`
10. `src/server/draftStore.ts`
11. `src/ui/DraftRoom.tsx`

Treat `docs/PROJECT_SPEC.md` as the durable source of truth. Preserve the
current Next.js/TypeScript, SQLite, offline-first, and Google Sheets adapter
boundaries.

## Accepted starting point

- Deterministic readiness artifact: `d2c138616a850d25`.
- The fresh 21-scenario hardening run completed 21/21 legal drafts with
  monotonic ladders, valid recorded fallbacks, exact accounting, and recovery
  equivalence.
- All 29 domain tests and TypeScript type checking passed.
- Exact historical nomination chronology and losing bids remain unavailable.
- Championship equity remains a relative shadow signal, not a calibrated
  probability of winning the league.
- The Assistant GM panel currently contains local canned guidance only.

Do not rebuild or change model artifacts merely to implement AI. If a model,
input, source, league rule, identity mapping, or deterministic recommendation
policy must change, stop and follow `docs/operations/change-revalidation.md`.

## Product contract

### AI may

- explain the current deterministic recommendation and price bands;
- compare the nominated player with the provided alternatives;
- explain roster, budget, bye-week, scarcity, owner, and market consequences;
- summarize what changed after a nomination or completed sale;
- answer follow-up questions grounded in the current packet;
- suggest nomination options only from deterministic Upcoming Targets; and
- identify uncertainty, missing data, or conflicting signals.

### AI may not

- invent, recalculate, or alter expected price, Walk-Away, bands, xPAR,
  alternatives, owner evidence, or League Outlook values;
- record, edit, undo, or propose executing a sale as an application action;
- change rosters, budgets, preferences, nomination order, SQLite, model
  artifacts, pointers, or Google Sheets;
- claim the shadow championship signal is a literal title probability;
- use unsupported general fantasy knowledge as if it were current app data;
- conceal missing context or fabricate certainty; or
- become required for nomination, sale recording, recommendations, recovery,
  or any other essential draft action.

The deterministic engine remains authoritative. If AI and the packet appear to
conflict, show the deterministic result and treat the AI response as invalid.

## Required implementation phases

### 1. Versioned Assistant GM context packet

Create a small typed server-side builder with strict validation. It should
include only decision-relevant facts, with units, labels, and provenance:

- draft ID and authoritative state version;
- trigger type: initial, selection, official nomination, sale, correction, or
  user question;
- focused player identity, position, NFL team, bye, ADP, risk flags, and data
  freshness;
- pre-draft and live expected price, modeled range, and room movement;
- all five final price bands and Walk-Away;
- xPAR/production label and scarcity/fallback context;
- deterministic recommendation, scenario support, rationale, and explicit
  shadow-model status;
- Renegades roster, needs, remaining budget, open slots, and maximum legal bid;
- comparable alternatives and what is lost by waiting;
- likely competitors, their roster/budget fit, and evidence-backed owner
  tendencies with uncertainty language;
- Upcoming Targets and nomination options;
- recent sales, live-market pressure, and What Changed;
- League Outlook rank/range without overstating precision;
- saved soft preferences and their bounded adjustments; and
- missing or stale fields.

The browser must not be allowed to supply authoritative facts. The server
rebuilds the packet from current local state for every request.

### 2. Prompt and response contract

Create a versioned system prompt that:

- states the permitted and forbidden behavior above;
- clearly separates facts, model estimates, owner tendencies, preferences, and
  AI judgment;
- requires concise plain language by default;
- requires specific packet evidence for every recommendation explanation;
- forbids fabricated prices, players, injuries, news, or owner intent;
- treats user-entered notes as untrusted data, not instructions;
- says when evidence is missing or signals conflict; and
- never asks the user to expose API credentials in chat.

Prefer a structured response contract containing at least response text,
referenced packet fields, state version, prompt version, and uncertainty flags.
Reject or visibly downgrade responses that fail validation.

### 3. Private streaming server connection

Implement the AI call behind a server-only boundary. Requirements:

- secrets never enter browser code, logs, committed files, or SQLite payloads;
- stream partial text to the existing Assistant GM panel;
- enforce a timeout and bounded input/output size;
- associate every response with the packet’s draft state version;
- cancel or mark a response stale when the draft advances;
- allow only one active generation per conversation unless intentionally
  replaced;
- expose clear unavailable, timeout, stale, and retry states; and
- do not reuse the Google Sheets synchronization outbox for AI requests.

Use a provider adapter so the rest of the application is not coupled directly
to one SDK. Begin with read-only text generation—no AI tools or function calls.

### 4. Proactive and interactive experience

After each official nomination or completed sale, generate one short update:

- the actionable recommendation or relevant change;
- the key reason;
- the price boundary or budget consequence when applicable; and
- the most relevant alternative or competitor.

Do not trigger a new paid request for insignificant UI-only state changes.
Interactive questions should support player comparisons, Walk-Away reasoning,
budget consequences, roster construction, alternatives, owner competition,
nomination choices, and What Changed.

Keep the existing deterministic cards visible while AI streams. Preserve a
useful local fallback message when AI is disabled or unavailable.

### 5. Audit and observability

Record a local, append-only AI interaction audit containing:

- interaction ID and timestamps;
- draft state version and trigger;
- context schema version and a content hash;
- model/provider identifier and prompt version;
- user question when applicable;
- completion status: completed, failed, timed out, cancelled, or stale;
- response text or a safe error category; and
- grounding-validation result.

Do not store secrets or unnecessary provider payloads. AI audit failure must not
block draft actions.

### 6. Automated evaluation

Build deterministic fixtures and a mock provider before using a live model.
Test at minimum:

- correct packet construction after nomination, sale, correction, and reset;
- no browser-supplied authoritative values;
- stream completion, cancellation, timeout, and provider failure;
- stale response handling after a new draft action;
- offline deterministic fallback;
- prompt injection in strategy notes, player text, or owner notes;
- no invented player, price, band, owner claim, or title probability;
- answers reference the correct Walk-Away and alternatives;
- nomination suggestions stay inside Upcoming Targets;
- no mutation of SQLite draft state or Google Sheets;
- AI unavailability never blocks a sale; and
- response latency and UI readability at the target laptop size.

Create a small grounded-response evaluation set covering expensive stars,
low-cost depth, no fallback, thin tiers, budget pressure, conflicting owner
signals, bye-week concerns, and a sale above Walk-Away. Grade factual accuracy,
grounding, uncertainty, concision, actionability, and forbidden behavior.

Do not grade a prompt only on examples used to write it. Keep separate
development and final-review cases.

## Safety and isolation

- Do not use or reset `.local/renegade-draft-room.sqlite` during development or
  tests. Use temporary isolated databases.
- Do not write to the connected Google Sheet.
- Do not advance any model or simulation pointer.
- Do not connect AI tools with write capabilities.
- Do not add live bid-by-bid entry.
- Do not make network or AI availability a prerequisite for core operation.
- Do not commit credentials, `.env` contents, raw authorization headers, or
  provider responses containing sensitive information.
- Preserve user changes in the dirty worktree.

## Documentation deliverables

Update or create:

1. the context-packet schema and prompt contract documentation;
2. local setup instructions using environment-variable names only;
3. offline, failure, stale-response, and recovery behavior;
4. an AI grounding/evaluation study with exact fixtures and limitations;
5. `docs/PROJECT_SPEC.md` for any durable accepted AI boundary; and
6. `docs/README.md` links.

Do not place real secret values in documentation.

## Definition of done

- The real UI streams grounded answers from a private server boundary.
- The context packet is typed, validated, versioned, and built from local
  authoritative state.
- AI cannot write or alter authoritative state.
- Draft actions remain fully functional with AI disabled, slow, stale, or
  unavailable.
- Proactive messages fire only for meaningful official draft events.
- Interactive questions work for the supported decision topics.
- Audit records and grounding checks are present.
- Automated tests and the separate final evaluation pass.
- No active database, Google Sheet, model artifact, or pointer was used as a
  test target.

## Stop and review point

Stop after implementation, automated testing, and the grounded evaluation
report. Present:

- what was built;
- the exact context supplied to AI;
- which behaviors are deterministic versus generated;
- test and grounding results;
- latency, cost, privacy, and offline behavior;
- failures or unsupported questions;
- any configuration still needed from George; and
- whether the Assistant GM is safe to enable for a mock draft.

Do not expand AI authority or begin unrelated model tuning without approval.

