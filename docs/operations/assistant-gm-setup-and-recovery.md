# Assistant GM Setup, Failure, and Recovery

No configuration is required for the grounded mock provider. It runs locally
and demonstrates the complete streaming path without network access.

Optional live text generation uses environment variables only:

- `ASSISTANT_GM_PROVIDER=openai`
- `OPENAI_API_KEY` (server process only)
- `ASSISTANT_GM_MODEL` (optional)
- `ASSISTANT_GM_TIMEOUT_MS` (optional; default 12000)
- `ASSISTANT_GM_AUDIT_PATH` (optional; defaults under `.local/`)

Never place values in browser code, documentation, SQLite payloads, or logs.
The server sends no tools and does not log provider requests or authorization
headers.

On unavailability, provider failure, timeout, cancellation, invalid grounding,
or a state-version change, the generated answer is visibly downgraded or
discarded. The deterministic recommendation, ladder, Upcoming Targets, sale
recording, correction, reset, persistence, and recovery remain available. A
retry always rebuilds context from current local state. AI requests never use
the Google Sheets outbox and audit-write failure never blocks a draft action.

The append-only JSONL audit records IDs/timestamps, state and schema versions,
context SHA-256, provider/model and prompt version, question, safe completion
status, response text only on success, and grounding result. It excludes
secrets and raw provider payloads.

