# Renegade Draft Room — Product Notes

This is the durable working file for ideas, questions, and topics that need
more discussion. Items here are not settled requirements. When a decision is
made, move the resulting product or architecture contract into
`docs/PROJECT_SPEC.md` and the relevant detailed document.

## Recommendation explanation: reasons to draft or pass

Add two concise, player-specific sections to the live recommendation:

- **Draft this player because**
- **Don't draft this player because**

The recommendation engine or AI should explain both sides relative to the
actual decision context, including:

- the player's expected price, production value, and current live price;
- roster construction and remaining budget;
- positional scarcity and replacement-level alternatives;
- comparable players who may be available later or for less money;
- opportunity cost—what the same dollars could buy elsewhere;
- relevant player, team, bye-week, and risk preferences;
- likely competition and the risk that the room pushes the price higher;
- uncertainty in both projected production and predicted sale price.

The purpose is not to produce generic player pros and cons. Each side should
answer the live question: *why is drafting or passing on this player better
than the realistic alternatives available to the Rodman Renegades right now?*

### Questions to resolve

- Should both sections always be visible, or should the stronger conclusion be
  shown first with the counterargument collapsed?
- How many reasons can be displayed without making the draft screen noisy?
- Which statements must come from deterministic calculations, and which are
  appropriate for AI synthesis?
- How should evidence strength and uncertainty be communicated?

## Overall success metric

Revisit the application's ultimate objective. Maximizing projected production
value above auction cost is useful, but it is probably an intermediate metric,
not the final definition of success.

The more meaningful objective may be to maximize the probability that the
completed roster:

1. reaches the fantasy playoffs; and
2. wins the league championship.

Evaluating that objective would require estimating outcomes across the season,
not just totaling draft-day values. A future roster-outcome layer could:

- simulate weekly player points from projection distributions;
- incorporate lineup rules, bench depth, bye weeks, injuries, and correlated
  player outcomes;
- model replacement players, waivers, and possibly trades at an appropriate
  level of complexity;
- simulate opponents' completed rosters and the league schedule;
- estimate playoff qualification, playoff advancement, and championship
  probabilities;
- compare a contemplated purchase with realistic alternative draft paths;
- update those probabilities after every sale as the set of attainable rosters
  changes.

This suggests a hierarchy of measures rather than one score:

- **Draft-decision measures:** expected price, surplus, opportunity cost, and
  roster fit.
- **Roster-quality measures:** projected points, weekly ceiling/floor, depth,
  fragility, and bye-week coverage.
- **Outcome measures:** playoff probability and championship probability.

### Questions to resolve

- Is championship probability the primary optimization target, with playoff
  probability shown as a secondary safety measure?
- How much variance should we intentionally accept for championship upside?
- What historical seasons can validate whether simulated probabilities are
  calibrated?
- How should in-season waivers, injuries, trades, and manager behavior be
  represented without creating false precision?
- Should the live recommendation show the estimated change in playoff and
  championship probability from buying the nominated player versus passing?

## Room notes for the AI situational read

Add a lightweight **Room notes** feature for observations that the application
cannot infer from nominations and completed sales alone. During the draft, the
operator could quickly record short notes such as `RB panic`, `room conserving
money`, `Chris is chasing Cowboys`, or `several owners dropped out early`.

Room notes should:

- be fast to add without creating a live bid-entry workflow;
- accept free-form notes and a small set of optional quick tags;
- retain timestamps and, when relevant, links to a player, owner, position, or
  nomination;
- be persisted locally and remain available after restart;
- provide context to the AI Copilot's situational read and explanations;
- be labeled as operator observations rather than verified draft facts; and
- never directly change authoritative draft state, hard constraints, market
  calculations, or deterministic recommendations.

If the Copilot uses a room note to challenge or adjust its advice, it should
identify the note and explain the effect. The deterministic baseline remains
visible so the operator can compare the calculated recommendation with the AI's
room-aware judgment.

### Questions to resolve

- Which quick tags would be useful enough to justify permanent controls?
- Should notes expire automatically, or should the operator mark them as
  temporary, persistent, or resolved?
- Should the AI infer candidate room notes and ask for confirmation?
- How should contradictory or stale observations affect AI confidence?
- Where can notes be entered and reviewed without crowding the main draft flow?

## Upcoming Targets and draft roadmap

Add an **Upcoming Targets** view that answers: *Who should the Rodman Renegades
be preparing to pursue next, in what order, and at what prices to maximize the
product's current success metric?* This should be a continuously recalculated
draft roadmap rather than a static player ranking.

For each recommended target, show:

- priority order and the role the player would fill;
- recommended purchase range, target price, and walk-away ceiling;
- the expected effect on the current success metric, including championship
  equity when that model is available;
- why this player is preferred over realistic alternatives;
- the next-best replacement and the expected cost of waiting;
- remaining supply at the position, tier membership, players left in the tier,
  and the risk that the tier closes before the Renegades can act;
- roster need, remaining budget, open slots, flexibility, bye-week effects, and
  opportunity cost across other positions;
- the operator's personal draft strategy, including players to target or avoid,
  NFL teams and team-position situations to target or avoid, roster-construction
  preferences, risk tolerance, bye-week philosophy, and any documented strategy
  notes;
- likely competing owners, their needs and budgets, and relevant supported
  tendencies; and
- confidence, important assumptions, and the event that would invalidate or
  reorder the recommendation.

The roadmap should include conditional branches rather than pretending the
rest of the auction is predictable. Examples:

- **If acquired at or below the target price:** update the remaining roster
  plan, budget allocation, and next targets.
- **If bidding exceeds the ceiling:** pass and promote the named replacement or
  alternate roster path.
- **If another owner buys a key player:** recalculate positional supply,
  competitor needs, and the probability that alternatives reach the Renegades.
- **If a tier run begins:** show whether to act now, pivot positions, or accept
  replacement-level production and preserve money elsewhere.

The system should be capable of running a read-only **autopilot simulation**:
using all locally available projections, expected and live prices, remaining
players, tiers, replacement costs, roster constraints, opponent states, owner
tendencies, the operator's complete personal draft strategy, and outcome models,
simulate the purchases and price limits it would choose from the current state
through roster completion. Present the resulting roster paths, expected spend,
and success metric so the operator can understand the longer-term consequences
of the next decision.

Personal strategy inputs should influence target order, acceptable price,
replacement paths, and the explanation for each recommendation. The roadmap
must identify material strategy adjustments explicitly—for example, `moved up
because this player is a target` or `excluded from the primary path because this
team-position combination is marked avoid`. Preferences remain bounded advisory
inputs: they may change the Renegades-specific plan but must not alter objective
market-price evidence, make an available player unavailable, or override hard
roster and budget constraints. The operator should be able to distinguish a
model-driven recommendation from one materially influenced by personal
strategy.

Autopilot is advisory only. It may propose nominations, purchases, passes, and
price ceilings, but it must never nominate a player, record a sale, or otherwise
mutate authoritative draft state without an explicit user action. Hard roster
and budget constraints remain deterministic. AI may interpret room conditions,
room notes, and strategic tradeoffs, but any AI adjustment should appear beside
the deterministic roadmap baseline with its reasoning and confidence.

The roadmap must refresh after every nomination, completed sale, correction,
strategy change, or room note that materially changes the situational read. It
should preserve enough of the prior plan to explain why priorities changed
instead of presenting an unexplained new list.

### Questions to resolve

- Should the primary view show a short ranked queue, a branching decision tree,
  or both at different levels of detail?
- How many future roster paths can be shown without implying false precision?
- Should target order optimize expected championship equity, a risk-adjusted
  version of it, or a user-selectable objective?
- How strongly should each personal strategy preference influence target order
  and price ceilings, and should the roadmap offer a comparison with those
  preferences temporarily disabled?
- How should nomination strategy differ from acquisition priority—for example,
  nominating players the Renegades do not want in order to drain opponent
  budgets?
- How should the planner model uncertain sale order and prices while remaining
  fast enough to recalculate during a live auction?
- Which roadmap changes should trigger a proactive alert rather than silently
  reordering the queue?

## Google draft-board integrity and repair

SQLite remains the authoritative draft state. Manual changes made directly in
Google Sheets must never change rosters, budgets, availability, history, or
recommendations inside Renegade Draft Room.

The current full-snapshot synchronization already repairs Player and Price
cells on the next sale, correction, or retry:

- a deleted or mistyped player is restored;
- a changed price is restored;
- a player moved into the wrong roster row or owner block is cleared and
  returned to the locally recorded slot;
- the application does not repair position labels, formulas, formatting, or
  other cells because its write boundary intentionally covers only Player and
  Price cells.

### Additions to consider

- Add an always-available **Repair Google Board** action that republishes the
  complete authoritative roster snapshot without requiring a new sale or a
  failed-sync state.
- Add periodic drift detection that compares the Sheet's Player and Price cells
  with SQLite.
- Surface a concise **Board changed externally** warning when drift is found.
- Allow automatic repair of detected drift, while never importing Sheet edits
  into local draft state.
- Record detected drift and repair results in an operational audit trail.
- Distinguish connection failures, permission/protection failures, pending
  writes, detected drift, and successful synchronization in the UI.

### Sheet-permission recommendation

Protect all Player and Price ranges so only the operator and the dedicated
service account can edit them. Other league members should normally receive
Viewer access. If they require Editor access elsewhere in the workbook, retain
range protection around the application-managed cells.

Service account currently assigned to the draft board:

```text
jugg-league-draft-room@fantasy-football-506423.iam.gserviceaccount.com
```

### Questions to resolve

- Should drift be repaired automatically or require one click during the live
  draft?
- How frequently should drift detection run without creating unnecessary
  network traffic or Google API dependence?
- Should position labels and formulas also be verified, even though the app
  should continue avoiding writes outside Player and Price cells?
- How should an intentional commissioner edit be handled if the local draft
  state is wrong? The likely answer is to correct the sale in Renegade Draft
  Room and let the app republish the board, rather than editing Sheets directly.
