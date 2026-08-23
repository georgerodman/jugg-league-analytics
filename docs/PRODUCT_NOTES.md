# Renegade Draft Room — Product Notes

This is the durable working file for ideas, questions, and topics that need
more discussion. Items here are not settled requirements. When a decision is
made, move the resulting product or architecture contract into
`PROJECT_SPEC.md` and the relevant detailed document.

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
