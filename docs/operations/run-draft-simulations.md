# Running the isolated draft simulations

Run the baseline suite from the repository root:

```bash
npm run test:simulation
```

The runner creates a uniquely named database under the operating system's
temporary directory for each scenario and removes it after the run. It never
opens `.local/renegade-draft-room.sqlite`, never calls Google Sheets, and never
uses a network or AI service. Outbox success, pending, and failure behavior is
represented locally in the temporary database.

Results are written beneath `data/processed/draft_simulations/<build-id>/` and
the local pointer is `data/processed/draft_simulations/latest.json`. The build
ID is derived from the code revision, artifact build IDs, seeds, and documented
assumptions. A repeated run with the same inputs writes the same version.

The suite exits unsuccessfully if any valid full-draft scenario fails to reach
140 sales or violates the core accounting/recovery checks.

For a review run that must not replace the accepted simulation pointer, provide
an unused seed offset and disable publication:

```bash
SIM_SEED_OFFSET=130000 \
SIM_RUN_LABEL=deterministic-readiness-review \
SIM_PUBLISH_LATEST=false \
npm run test:simulation
```

Historical scenario families use actual JUGG prices for historical players who
also exist in the current decision pool. They preserve the actual buyer when
that purchase remains legal in the generated order. Results report total
season sales, compatible players, actual prices used, buyers preserved, and
buyers substituted for legality. The order remains generated because exact
historical nomination chronology is unavailable.

See [Change and Revalidation Workflow](change-revalidation.md) before accepting
results after any model, input, data-source, or recommendation change.
