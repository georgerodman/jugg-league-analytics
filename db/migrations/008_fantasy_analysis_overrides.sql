CREATE TABLE fantasy_analysis_overrides (
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  player_id TEXT NOT NULL REFERENCES players(id),
  override_value TEXT NOT NULL CHECK (override_value IN ('target','avoid','off')),
  updated_at TEXT NOT NULL,
  PRIMARY KEY (draft_id, player_id)
);

INSERT INTO schema_migrations(version, name) VALUES (8, 'fantasy_analysis_overrides');
