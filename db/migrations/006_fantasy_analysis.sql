CREATE TABLE fantasy_analysis_sources (
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL REFERENCES artifact_imports(id),
  source_key TEXT NOT NULL,
  title TEXT NOT NULL,
  author TEXT,
  url TEXT NOT NULL,
  published_at TEXT NOT NULL,
  season INTEGER NOT NULL CHECK (season >= 2020),
  content_type TEXT NOT NULL,
  imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE fantasy_player_takeaways (
  source_id TEXT NOT NULL REFERENCES fantasy_analysis_sources(id),
  player_id TEXT NOT NULL REFERENCES players(id),
  label TEXT NOT NULL CHECK (label IN ('sleeper','target','avoid','bust','value','breakout')),
  sentiment TEXT NOT NULL CHECK (sentiment IN ('positive','mixed','negative')),
  summary TEXT NOT NULL,
  rationale TEXT NOT NULL,
  risks_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(risks_json)),
  PRIMARY KEY (source_id, player_id, label)
);

CREATE INDEX fantasy_takeaways_by_player ON fantasy_player_takeaways(player_id);
INSERT INTO schema_migrations(version, name) VALUES (6, 'fantasy_analysis');
