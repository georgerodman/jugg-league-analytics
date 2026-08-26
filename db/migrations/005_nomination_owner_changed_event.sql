PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

-- A prior interrupted attempt may have created this shadow table before the
-- migration version was committed. Rebuild it from the authoritative table.
DROP TABLE IF EXISTS draft_events_v5;

CREATE TABLE draft_events_v5 (
  id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  sequence INTEGER NOT NULL CHECK (sequence > 0),
  event_type TEXT NOT NULL CHECK (event_type IN (
    'draft_created','draft_started','nomination_opened','nomination_cancelled','nomination_owner_changed',
    'sale_recorded','sale_voided','roster_slot_reassigned','draft_completed'
  )),
  aggregate_type TEXT NOT NULL,
  aggregate_id TEXT NOT NULL,
  idempotency_key TEXT NOT NULL,
  payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
  occurred_at TEXT NOT NULL,
  recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (draft_id, sequence),
  UNIQUE (draft_id, idempotency_key)
);

INSERT INTO draft_events_v5
SELECT id,draft_id,sequence,event_type,aggregate_type,aggregate_id,idempotency_key,payload_json,occurred_at,recorded_at
FROM draft_events;

DROP TRIGGER IF EXISTS draft_events_no_update;
DROP TRIGGER IF EXISTS draft_events_no_delete;
DROP TABLE draft_events;
ALTER TABLE draft_events_v5 RENAME TO draft_events;

CREATE TRIGGER draft_events_no_update
BEFORE UPDATE ON draft_events BEGIN SELECT RAISE(ABORT, 'draft events are immutable'); END;
CREATE TRIGGER draft_events_no_delete
BEFORE DELETE ON draft_events BEGIN SELECT RAISE(ABORT, 'draft events are immutable'); END;
CREATE INDEX events_for_recovery ON draft_events(draft_id, sequence);

INSERT INTO schema_migrations(version, name) VALUES (5, 'nomination_owner_changed_event');

COMMIT;
PRAGMA foreign_keys = ON;
