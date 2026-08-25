CREATE TABLE draft_nomination_order (
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  team_id TEXT NOT NULL REFERENCES teams(id),
  ordinal INTEGER NOT NULL CHECK (ordinal > 0),
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (draft_id, team_id),
  UNIQUE (draft_id, ordinal)
);

CREATE TABLE team_draft_completions (
  id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  team_id TEXT NOT NULL REFERENCES teams(id),
  completed_event_id TEXT NOT NULL REFERENCES draft_events(id),
  completed_at TEXT NOT NULL,
  voided_event_id TEXT REFERENCES draft_events(id),
  UNIQUE (completed_event_id)
);

CREATE UNIQUE INDEX one_active_completion_per_team
ON team_draft_completions(draft_id, team_id)
WHERE voided_event_id IS NULL;

INSERT INTO schema_migrations(version, name) VALUES (3, 'nomination_and_waiver_order');
