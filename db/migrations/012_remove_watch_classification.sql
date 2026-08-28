ALTER TABLE fantasy_analysis_overrides RENAME TO fantasy_analysis_overrides_old;

CREATE TABLE fantasy_analysis_overrides (
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  player_id TEXT NOT NULL REFERENCES players(id),
  override_value TEXT NOT NULL CHECK (override_value IN ('target','avoid','off')),
  updated_at TEXT NOT NULL,
  PRIMARY KEY (draft_id, player_id)
);

INSERT INTO fantasy_analysis_overrides(draft_id,player_id,override_value,updated_at)
SELECT draft_id,player_id,
  CASE override_value WHEN 'watch' THEN 'off' ELSE override_value END,
  updated_at
FROM fantasy_analysis_overrides_old;

DROP TABLE fantasy_analysis_overrides_old;

INSERT INTO schema_migrations(version, name) VALUES (12, 'remove_watch_classification');
