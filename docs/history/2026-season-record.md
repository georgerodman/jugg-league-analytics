# 2026 Season Record

This is the compact historical record for the first completed Renegade Draft
Room season. Detailed development studies, implementation briefs, intermediate
results, and superseded product notes remain recoverable from Git tag
`draft-2026-final`.

## Final draft record

- Draft ID: `jugg-2026`
- Finalized: August 30, 2026 at `16:34:46.994Z`
- Final state: 140 sales, 309 events, no open nomination
- Lifecycle: `complete`; all draft mutations are locked
- Google Sheets synchronization: permanently disabled for this draft
- Local final backup: `.local/backups/renegade-draft-room-final-2026-08-30T16-34-46-994Z.sqlite`
- Durable external archive: copied outside the repository by the operator
- Source-control checkpoint: `draft-2026-final`

The external archive is the preservation copy. The ignored local backup is a
convenience copy and should not be the only retained record.

## Accepted 2026 approach

- FantasyPros preseason projections were the primary projection source; FFA
  was retained for enrichment and comparison.
- nflverse/GSIS supplied durable player identity and historical NFL outcomes.
- ESPN salary-cap values and ADP were market evidence, not intrinsic player
  value or draft-state authority.
- The application kept expected auction price separate from projected
  production value.
- Owner tendencies remained probabilistic context, never a deterministic claim.
- The championship signal remained a relative, schedule-neutral shadow ranking,
  not a calibrated probability of winning the league.
- SQLite was authoritative during the draft. Google Sheets was an optional
  outbound view and could not block or overwrite local draft actions.
- The Assistant GM was bounded to explaining deterministic local facts. It
  could not mutate draft state, invent prices, or become required for core use.

## Final validation evidence

The accepted system completed 21 of 21 fresh deterministic full-draft
scenarios legally, with monotonic price ladders, valid fallback references,
budget and roster conservation, and equivalent recovery after reopening each
temporary SQLite database.

The historical price benchmark used a forward-held-out cohort of 700 JUGG
sales from 2021–2025. The combined evidence-selected model outperformed the
tested single market inputs, but its prices remained estimates and were shown
with ranges. Exact historical nomination order and losing bids were not
available, so the project did not claim counterfactual proof that a particular
recommendation would have won a past draft.

FantasyPros had lower MAE and RMSE than FFA on the shared 2020–2025 offensive
player-season cohort used in the projection comparison. That supported the
primary/enrichment source roles above; it did not make either provider a source
of permanent identity or historical truth.

## Important limitations carried forward

- Preseason projections and research writeups are dated snapshots. The 2026
  writeups are intentionally frozen and are not a live in-season research feed.
- A future in-season summary system should be a new workflow with dated source
  inputs, not a refresh of the frozen draft summaries.
- Provider availability, schemas, terms, and scoring context must be reviewed
  again before a new season is published.
- A finalized draft is immutable. Start the next season with a new draft ID,
  new local state, and an explicitly configured new Google Sheet mapping.

## Recovering detailed historical documents

To inspect the complete documentation tree as it existed at finalization:

```sh
git ls-tree -r --name-only draft-2026-final docs
git show draft-2026-final:docs/studies/deterministic-readiness-review.md
```

Do not restore old documents into the active tree merely to preserve history;
Git and the external finalized archive already provide that record.
