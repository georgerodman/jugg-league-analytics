ALTER TABLE fantasy_analysis_overrides RENAME TO fantasy_analysis_overrides_old;

CREATE TABLE fantasy_analysis_overrides (
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  player_id TEXT NOT NULL REFERENCES players(id),
  override_value TEXT NOT NULL CHECK (override_value IN ('target','avoid','watch','off')),
  updated_at TEXT NOT NULL,
  PRIMARY KEY (draft_id, player_id)
);

INSERT INTO fantasy_analysis_overrides(draft_id,player_id,override_value,updated_at)
SELECT draft_id,player_id,override_value,updated_at FROM fantasy_analysis_overrides_old;

DROP TABLE fantasy_analysis_overrides_old;

CREATE TABLE fantasy_analysis_tag_overrides (
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  player_id TEXT NOT NULL REFERENCES players(id),
  tag TEXT NOT NULL CHECK (tag IN ('sleeper','breakout','value','bust')),
  enabled INTEGER NOT NULL CHECK (enabled IN (0,1)),
  updated_at TEXT NOT NULL,
  PRIMARY KEY (draft_id, player_id, tag)
);

INSERT INTO schema_migrations(version, name) VALUES (11, 'fantasy_classification_overrides');
