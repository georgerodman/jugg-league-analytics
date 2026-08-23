ALTER TABLE draft_player_pool ADD COLUMN adp_espn REAL;
ALTER TABLE draft_player_pool ADD COLUMN adp_yahoo REAL;
ALTER TABLE draft_player_pool ADD COLUMN bye_week INTEGER CHECK (bye_week IS NULL OR bye_week BETWEEN 4 AND 18);

CREATE TABLE draft_strategy (
  draft_id TEXT PRIMARY KEY REFERENCES drafts(id),
  strategy_json TEXT NOT NULL CHECK (json_valid(strategy_json)),
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE player_preferences (
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  player_id TEXT NOT NULL REFERENCES players(id),
  preference TEXT NOT NULL CHECK (preference IN ('target','avoid')),
  premium INTEGER NOT NULL DEFAULT 0 CHECK (premium BETWEEN -50 AND 50),
  note TEXT,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (draft_id, player_id)
);

INSERT INTO schema_migrations(version, name) VALUES (2, 'strategy_and_market_context');
