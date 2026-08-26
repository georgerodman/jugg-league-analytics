CREATE TABLE fantasy_player_summaries (
  player_id TEXT PRIMARY KEY REFERENCES players(id),
  summary TEXT NOT NULL,
  source_ids_json TEXT NOT NULL CHECK (json_valid(source_ids_json)),
  input_hash TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  model TEXT NOT NULL,
  generated_at TEXT NOT NULL
);

CREATE TABLE fantasy_team_context (
  source_id TEXT NOT NULL REFERENCES fantasy_analysis_sources(id),
  nfl_team TEXT NOT NULL,
  environment TEXT NOT NULL CHECK (environment IN ('strong','favorable','neutral','uncertain','weak')),
  summary TEXT NOT NULL,
  risks_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(risks_json)),
  PRIMARY KEY (source_id, nfl_team)
);

INSERT INTO schema_migrations(version, name) VALUES (9, 'fantasy_research_synthesis');
