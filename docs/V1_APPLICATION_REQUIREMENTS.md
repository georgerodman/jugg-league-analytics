# Renegade Draft Room — V1 Requirements

## Product identity

- Application name: **Renegade Draft Room**.
- Operator team: **Rodman Renegades**.
- The product should feel like a focused draft console, not an analytics
  dashboard. Its visual hierarchy should communicate what matters without
  requiring the operator to interpret a wall of metrics.

## V1 outcome

V1 must let one local operator run the entire 2026 JUGG auction from a single
screen without internet access. The operator can find and nominate a player,
evaluate that player, record the final winner and sale price, see budgets and
rosters update immediately, correct mistakes safely, and recover the exact
state after restarting the application.

Success is operational confidence, not feature breadth. If a capability is not
needed to complete or recover the draft, it should not delay V1.

## Primary user and environment

- One operator controls the application on a laptop during the in-person or
  remote auction.
- Other managers do not log into V1.
- The application runs locally and stores authoritative state in SQLite.
- Internet, AI, and Google Sheets may be unavailable without impairing core
  operation.
- The primary target is a maximized browser window on a 15-inch MacBook Pro.
  Design against an approximately 1680 × 950 usable browser viewport while
  remaining functional down to 1440 × 800. Use the full canvas efficiently,
  but do not fill available space merely because it exists. Phone operation is
  not a V1 goal.

## Design principle: less is more

The default screen should show only information needed for the next decision.
Supporting evidence remains one click away in drawers, tooltips, or expandable
rows. The operator should not need to read every model input to trust or use a
recommendation.

- Prefer one clear answer with a short explanation over several competing
  metrics.
- Use whitespace, alignment, and typography instead of boxes around everything.
- Avoid decorative charts, redundant labels, and permanently visible detail.
- Show exceptions and risks when they matter; do not display reassuring
  no-warning states.
- Reveal model provenance and methodology on demand.
- Keep the current nomination and final-sale action visually dominant.
- Default lists should have few columns and predictable scanning order.

## Required V1 capabilities

### Draft preparation

- Create or reopen the 2026 local draft database.
- Import the current validated 294-player decision board and ten owner profiles.
- Show the artifact build IDs and warn if a required artifact is missing.
- Create all ten teams, budgets, and fourteen roster slots per team.
- Preselect and visually emphasize the Rodman Renegades without changing rules.
- Start the draft explicitly; setup actions cannot silently start it.

### Player discovery

- Search by player name with tolerant, fast matching.
- Filter by position, availability, draft-likelihood tier, and risk flags.
- Default to a single useful ranking. Additional sorting by expected price,
  production value, surplus, projected points, draft probability, or position
  rank is available without showing all fields as permanent columns.
- Clearly distinguish available, currently nominated, and sold players.
- Display why an excluded/deep player is not in the supported market pool.
- Show compact blended Yahoo/ESPN ADP and bye week columns.
- Sort by clicking the Player, ADP, Bye, Live Expected, or Edge header; clicking
  the active header reverses direction.

### Nominated-player decision support

The center of the screen is the current nomination. Its default view shows:

- player, position, NFL team, and concise rank context;
- expected JUGG price and range;
- one value verdict combining production value and expected surplus;
- Rodman Renegades roster fit;
- only material risk flags;
- one concise relevant owner-tendency insight, when supported; and
- up to three nearby alternatives.

Projected points, production value, draft probability, replacement details,
allocation sensitivity, ESPN auction value, Yahoo/ESPN ADP, full provenance,
and the complete owner evidence remain available in an expandable `Details`
view. Draft probability may appear by default only when it changes the decision,
such as a bubble player likely to remain available later.

There is no bid-entry stream. Bidding happens elsewhere.

### Final sale recording

- Select the winning team and enter the final integer sale price.
- Show that team's remaining budget, maximum legal price, open slots, and
  eligible destination slot before confirmation.
- Require one clear confirmation showing player, winner, and price.
- Commit locally in one transaction.
- Immediately update player availability, roster, budget, history, and all
  derived local recommendations.
- Prevent duplicate submissions, stale writes, invalid prices, ineligible
  rosters, duplicate sales, and violations of the $1-per-open-slot reserve.

### Corrections

- Cancel an open nomination without changing budgets or rosters.
- Void an incorrect completed sale from the history view with a reason and
  explicit confirmation.
- Restore the player, budget, and roster slot through a compensating event.
- Preserve the original action and correction in the audit history.
- A corrected sale is entered as a new action; history is never rewritten.

### Live league state

- Show every team's remaining budget, rostered count, open slots, and maximum
  legal bid.
- Expand a team to see filled and open roster slots.
- Highlight the operator's team.
- Show completed sales newest first.
- Show remaining players and positional supply.
- Show local market inflation/scarcity only when calculated from deterministic
  local state, with the calculation label available.
- Preserve the pre-draft expected price and show live expected price as a
  separately labeled, shrinkage-controlled adjustment from completed sales.

### Renegades strategy

- Provide a persistent strategy drawer for roster construction, risk tolerance,
  bye-week concentration, player preferences, NFL-team/position preferences,
  preferred situations, and notes.
- Support both preferred-player and player-to-avoid lists from the player view.
- Support preferred or avoided NFL teams, optionally scoped to a position.
- Treat every strategy input as advisory and bounded. No preference removes a
  player, blocks nomination or purchase, or modifies market-price evidence.
- Show material preference adjustments in the recommendation explanation.

### Recovery and offline status

- Reopen the most recent local draft automatically after process restart.
- Run the recovery audit before accepting a new action.
- Display a concise recovered-state notice after an interrupted session.
- Block mutation and provide a diagnostic if materialized state disagrees with
  the immutable event log.
- Show `Local state saved` after successful actions.
- Clearly show optional synchronization as pending, failed, or current, without
  treating a sync failure as a draft failure.

## Primary screen design

V1 uses the selected **Split Focus** direction: one draft-room page with a
restrained player list, a larger live-decision workspace, and quiet recent
history:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Renegade Draft Room · draft status · saved locally · quick actions │
├───────────────────┬───────────────────────────┬─────────────────────┤
│ Available players │ Current nomination + decision guidance         │
│ search + filters  │ roster fit · pressure · signals · alternatives │
├───────────────────┴─────────────────────────────────────────────────┤
│ Last few actions · expandable full history                         │
└─────────────────────────────────────────────────────────────────────┘
```

### Available-player region

- Compact, keyboard-friendly list rather than large cards.
- Search remains visible at all times.
- The selected row and nominated row have distinct non-color indicators.
- Default columns: player, position, expected price, and a compact value signal.
- Probability, projections, source values, and full risk detail appear on
  selection or through optional column controls.

### Nomination region

- Empty state prompts the operator to search or choose a player.
- Selecting a player previews details without changing authoritative state.
- `Nominate` is the explicit state-changing action.
- Once nominated, winner and price controls become the dominant action area.
- The default verdict is plain language. Model facts, source facts, and
  contextual judgment remain distinguishable in the expanded details.

### Teams region

- Compact ten-team budget table is always visible.
- Rodman Renegades are pinned and visually emphasized.
- Budget pressure and roster needs use text/icons in addition to color.
- Owner tendencies appear as at most one relevant sentence; full profiles are
  available separately and never occupy permanent draft-room space.

### History region

- Keep a compact **Last 5 picks** strip on the main draft screen, newest first.
- Each row shows player, winning team, sale price, and pick number; avoid extra
  model data in this recovery-oriented view.
- Give each recent sale a clearly labeled correction action that opens the
  existing `Void sale` confirmation flow. Do not immediately reverse a sale
  from a single click.
- Make the complete, auditable draft history available in an expanded panel or
  secondary history view.
- Corrections are visually linked to the original sale.
- Destructive-looking actions use `Void sale`, not `Delete`.

## Server and data boundaries

- Browser components never access SQLite directly.
- `src/server/` owns database lifecycle, read queries, input validation, and
  translation to typed `DraftService` commands.
- `src/domain/` remains independent of Next.js and React.
- Server responses expose purpose-built view models rather than raw table rows.
- Every mutation includes an idempotency key and expected draft version.
- The UI refreshes from authoritative state after every mutation; it does not
  assume its optimistic state became authoritative.

## Required view models

- `DraftRoomView`: draft status/version, current nomination, team summaries,
  recent events, local-save state, and sync summary.
- `PlayerListItemView`: identity, availability, core model values, position
  rank, and compact risk summary.
- `NominatedPlayerView`: complete decision data, alternatives, roster fit, and
  relevant owner signals.
- `TeamDetailView`: budget, legal maximum, filled/open slots, and roster.
- `SaleConfirmationView`: validated player, team, price, slot, post-sale budget,
  and reserve amount.
- `RecoveryView`: event/materialized versions, audit result, and remediation.

## Interaction and accessibility requirements

- `/` focuses player search.
- Arrow keys navigate search results; Enter previews the highlighted player.
- State-changing actions require explicit buttons and cannot be triggered by a
  single ambiguous keystroke.
- Focus returns to search after a completed sale.
- All controls have accessible names and visible keyboard focus.
- Color is never the only indicator of availability, value, risk, or errors.
- Monetary values use whole dollars for entry and avoid unnecessary decimal
  precision in the primary view.
- Error messages state what failed, why, and whether anything was saved.

## Performance requirements

- Search/filter feedback should feel immediate and complete within 100 ms for
  the local 294-player pool.
- Nomination and sale actions should commit and refresh visible state within
  300 ms under normal local operation.
- Initial load should show usable local state within two seconds on the target
  laptop.
- No core action may wait for network access.

## V1 state and error cases

The interface must deliberately handle:

- no database / setup required;
- setup complete / draft not started;
- active draft with no nomination;
- active draft with an open nomination;
- mutation in progress;
- duplicate mutation replayed safely;
- stale state/version conflict;
- invalid sale or no eligible slot;
- recovered state after restart;
- recovery audit failure;
- draft complete;
- optional sync pending or failed; and
- missing or stale model artifact.

## V1 non-goals

- Live bid-by-bid entry
- Multi-user authentication or simultaneous editing
- Phone-first operation
- Google Sheets as authoritative state
- AI-required decisions or mutations
- Automated owner intent claims
- Nomination-timing predictions without ordered history
- Waivers, trades, weekly lineup management, or season-long league management
- Polished secondary analytics dashboards before the core draft workflow works

## Acceptance test

V1 is ready when a historical draft can be replayed from start to finish using
only the interface, producing the correct 140 sales, budgets, rosters, player
availability, and event history. During that replay:

1. interrupt and restart the application after a completed sale;
2. confirm exact recovery with no duplicate action;
3. disconnect the network and continue recording sales;
4. attempt an illegal reserve-breaking purchase and verify no state changes;
5. void and correctly re-enter a mistaken sale;
6. force optional synchronization failure and continue drafting; and
7. compare final state with the historical source and event audit.

## Confirmed visual defaults

V1 uses:

- dark, restrained, high-contrast theme suitable for prolonged use;
- **Renegade Draft Room** as the application title;
- **Rodman Renegades** as the pinned operator team;
- clean, sparse primary information with detail disclosed on demand;
- the **Split Focus** desktop layout;
- sale confirmation as a compact modal or anchored panel; and
- a compact **Last 5 picks** strip on the main screen, with safe correction
  controls and full history available on demand.

These choices affect presentation, not domain behavior, and can be changed
without revising the database or model contracts.
