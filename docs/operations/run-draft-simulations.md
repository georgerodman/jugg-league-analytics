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
