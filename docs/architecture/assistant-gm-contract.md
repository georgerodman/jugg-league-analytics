# Assistant GM Context and Prompt Contract

The Assistant GM is a read-only explanation layer over the deterministic Draft
Room. `assistant-gm-context.v1` is rebuilt on the server from the current local
SQLite-backed view for every request and validated strictly with Zod. The
browser may send only a trigger, a question, and a focus-player identifier; it
cannot supply prices, rosters, budgets, alternatives, owner claims, or state.
Dollar values explicitly entered in a question are retained separately as
non-authoritative hypothetical inputs so the AI can compare them with the
authoritative ladder without treating them as model outputs.

The packet contains draft ID/version and trigger; focused player identity,
freshness, risk, ADP, pre-draft/live prices and range; all five deterministic
bands and Walk-Away; production/xPAR/scarcity/fallback; recommendation, tested-
path support, rationale and shadow status; Renegades roster, needs, budget,
slots and legal maximum; alternatives; evidence-bounded competitors; Upcoming
Targets; compact league-wide rosters, needs, remaining budgets, open slots, and
legal maximum bids; recent sales, room pressure and What Changed; relative League Outlook;
bounded structured preferences; untrusted free-form notes; and missing/stale
fields. Dollar amounts are USD integers. Scenario support is a count of nine
paths. League Outlook is a relative shadow rank, not a title probability.

`assistant-gm-prompt.v1` states that the packet is the only authority. It
separates facts, estimates, tendencies, preferences, and generated judgment;
forbids outside news, invented facts, actions, tools, credentials, and
instructions embedded in notes; and requires uncertainty language. Responses
carry text, referenced packet fields, state/prompt versions, uncertainty flags,
and a grounding result. Unknown dollar claims, title-probability language, or
nomination choices outside Upcoming Targets invalidate the response. The UI
discards invalid or stale output and keeps deterministic cards visible.

Focused-player explanations use an action-first structure: what to do now, the
exact supported price range, the next threshold and reason for changing course,
and the relevant recorded alternatives or roster needs. Post-sale and
correction updates give a short radar list from the top deterministic Upcoming
Targets. When the local nomination rotation says the Renegades are next, the
same list is framed as nomination options with a grounded reason for each.

The provider adapter is private server code. It exposes read-only text streaming
with bounded input/output, timeout, cancellation, and one request per UI
conversation. It has no tools or function calls. The mock provider is the
default. A live provider is optional and never participates in draft writes.

For conversational continuity, the browser may return up to eight bounded
recent user/assistant turns. They are explicitly untrusted and used only for
pronouns, follow-ups, and tone; the server-built current state always overrides
conversation history. The AI may add clearly labeled strategic judgment and
general auction principles while preserving the official deterministic answer.
