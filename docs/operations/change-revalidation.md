# Change and Revalidation Workflow

Use this checklist whenever a model, input, data source, recommendation rule,
or live-draft data contract changes. A successful rebuild is not enough by
itself: generated numbers can be internally valid while making the complete
draft policy worse.

## Simple rule

Yes—changes to models, model inputs, source data, player matching, league rules,
or recommendation logic require the affected rebuild **and** another hardening
evaluation before draft-night use. Use new deterministic simulation seeds for
the final evaluation so the change is not graded only on scenarios used while
developing it.

Pure copy, color, spacing, or layout changes do not require model rebuilding,
but they still require type checks and a focused UI review. A UI change that
alters the meaning, ordering, availability, or calculation of advice is a
recommendation change and follows the stricter workflow below.

## Change classes

| Change | Rebuild needed | Minimum validation |
|---|---|---|
| Text, color, or spacing only | No | Type check, affected tests, visual review |
| Recommendation policy or threshold | No model rebuild | Domain tests, decision-edge tests, fresh-seed simulations, before/after recommendation audit |
| Projection, ADP, ESPN value, auction history, bye-week, or identity data | Yes | Source validation, full rebuild, board comparison, domain tests, fresh-seed simulations |
| Price, production, championship, owner, or draft-probability model | Yes | Model backtest, full rebuild, board comparison, domain tests, fresh-seed simulations |
| League budget, roster, scoring, or playoff rules | Yes | Update specification, rebuild dependent artifacts, legal-roster tests, fresh-seed simulations |
| SQLite schema or draft-state behavior | Usually not a model rebuild | Migration tests, transaction/recovery tests, isolated full draft, backup/reset drill |
| Google Sheets adapter | No model rebuild | Adapter tests plus offline/failure/retry drills; never test against the live sheet by default |

## Required sequence

1. **Record the change.** Identify the source snapshot, model version, code
   change, or rule change and which downstream artifacts depend on it.
2. **Validate external data boundaries.** Check schema, season, scoring format,
   row counts, missingness, duplicate identities, and match exceptions. Never
   silently force an uncertain player match.
3. **Rebuild affected artifacts.** Use the repository’s single-command rebuild
   workflow. Do not advance production pointers until the build and comparison
   have been reviewed.
4. **Review the board comparison.** Inspect additions, removals, large price or
   projection moves, tier changes, missing fields, and changed coverage.
5. **Run automated tests.** At minimum run:

   ```bash
   npm run typecheck
   npm run test:domain
   ```

6. **Run isolated full-draft evaluation with unused seeds.** Choose a seed
   offset not present in prior study artifacts and do not publish the result as
   latest during review:

   ```bash
   SIM_SEED_OFFSET=<unused-offset> \
   SIM_RUN_LABEL=<clear-review-name> \
   SIM_PUBLISH_LATEST=false \
   npm run test:simulation
   ```

7. **Compare against the last accepted version.** Report legal completion,
   monotonic ladders, Walk-Away changes, fallback validity, recovery,
   recommendation changes, source coverage, and any unintended effects.
8. **Approve or reject.** Only after review should an intentional release step
   advance a model or simulation pointer and rebuild the local draft database.
   Never use the active draft database or connected Google Sheet as a test
   target.

## Additional gates by change type

### Model or model-input changes

- Rerun the model’s forward-held-out backtest on the same neutral cohort.
- Compare the candidate with the currently accepted model and simple baselines.
- Use a separate, unused evaluation seed set for the final draft-policy test.
- Report which players, positions, price bands, and recommendation packets
  changed—not only aggregate accuracy.
- Do not advance `latest.json` pointers merely because the pipeline completed.

### New data sources

- Document source authority, scoring format, timing, and refresh method.
- Preserve the raw snapshot and provenance.
- Add strict boundary validation and identity-match exceptions.
- Measure overlap and missingness against existing sources.
- First test the candidate source on equal footing; do not grant it a preferred
  model role in advance.

### Recommendation changes

- Test prices below, at, and above Walk-Away.
- Verify final price ladders never improve as price rises.
- Test sold fallbacks, last-in-tier conditions, no close fallback, constrained
  budgets, and legal roster boundaries.
- Confirm that AI is not required and does not create or alter authoritative
  prices, bands, roster state, or sale records.

## Evidence to retain

Keep the candidate artifact IDs, exact seed list, code revision, source build
IDs, test output, comparison summary, known limitations, and approval decision.
Store repeatable procedures under `docs/operations/` and summarize accepted
empirical results in that season's document under `docs/history/`. Keep bulky
intermediate reports outside the active documentation tree once the season is
final. Update `docs/PROJECT_SPEC.md` only when a durable product or architecture
rule changes.
