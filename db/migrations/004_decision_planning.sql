CREATE TABLE decision_snapshots (
  id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  state_version INTEGER NOT NULL,
  trigger_type TEXT NOT NULL,
  trigger_key TEXT NOT NULL,
  snapshot_json TEXT NOT NULL CHECK (json_valid(snapshot_json)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (draft_id, trigger_key)
);
CREATE INDEX decision_snapshots_recent ON decision_snapshots(draft_id, created_at DESC);

CREATE TABLE nomination_decision_plans (
  nomination_id TEXT PRIMARY KEY REFERENCES nominations(id),
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  player_id TEXT NOT NULL REFERENCES players(id),
  recommended_ceiling INTEGER NOT NULL CHECK (recommended_ceiling > 0),
  committed_ceiling INTEGER NOT NULL CHECK (committed_ceiling > 0),
  adjustment_reason TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE discipline_overrides (
  id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  nomination_id TEXT NOT NULL REFERENCES nominations(id),
  sale_id TEXT NOT NULL REFERENCES sales(id),
  recommended_ceiling INTEGER NOT NULL,
  committed_ceiling INTEGER NOT NULL,
  actual_price INTEGER NOT NULL,
  reason TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_migrations(version, name) VALUES (4, 'decision_planning');
