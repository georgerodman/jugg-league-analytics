PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;

CREATE TABLE schema_migrations (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE drafts (
  id TEXT PRIMARY KEY,
  season INTEGER NOT NULL CHECK (season >= 2020),
  name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'setup' CHECK (status IN ('setup','active','complete','archived')),
  team_count INTEGER NOT NULL CHECK (team_count > 1),
  budget_per_team INTEGER NOT NULL CHECK (budget_per_team > 0),
  minimum_bid INTEGER NOT NULL CHECK (minimum_bid > 0),
  required_players_per_team INTEGER NOT NULL CHECK (required_players_per_team > 0),
  state_version INTEGER NOT NULL DEFAULT 0 CHECK (state_version >= 0),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE owners (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL UNIQUE,
  profile_json TEXT CHECK (profile_json IS NULL OR json_valid(profile_json)),
  profile_artifact_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE teams (
  id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  owner_id TEXT NOT NULL REFERENCES owners(id),
  display_name TEXT NOT NULL,
  starting_budget INTEGER NOT NULL CHECK (starting_budget > 0),
  UNIQUE (draft_id, owner_id),
  UNIQUE (draft_id, display_name)
);

CREATE TABLE team_draft_state (
  team_id TEXT PRIMARY KEY REFERENCES teams(id),
  remaining_budget INTEGER NOT NULL CHECK (remaining_budget >= 0),
  open_slot_count INTEGER NOT NULL CHECK (open_slot_count >= 0),
  rostered_player_count INTEGER NOT NULL DEFAULT 0 CHECK (rostered_player_count >= 0),
  version INTEGER NOT NULL DEFAULT 0 CHECK (version >= 0),
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE players (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  position TEXT NOT NULL CHECK (position IN ('QB','RB','WR','TE','K','DEF')),
  nfl_team TEXT,
  identity_status TEXT NOT NULL CHECK (identity_status IN ('stable','provisional')),
  source_ids_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(source_ids_json)),
  UNIQUE (display_name, position, nfl_team)
);

CREATE TABLE artifact_imports (
  id TEXT PRIMARY KEY,
  artifact_type TEXT NOT NULL,
  schema_version INTEGER NOT NULL CHECK (schema_version > 0),
  build_id TEXT NOT NULL,
  relative_path TEXT NOT NULL,
  sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
  imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  metadata_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(metadata_json)),
  UNIQUE (artifact_type, build_id, sha256)
);

CREATE TABLE draft_player_pool (
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  player_id TEXT NOT NULL REFERENCES players(id),
  status TEXT NOT NULL DEFAULT 'available' CHECK (status IN ('available','nominated','sold','removed')),
  expected_price REAL,
  price_low REAL,
  price_high REAL,
  draft_probability REAL CHECK (draft_probability IS NULL OR draft_probability BETWEEN 0 AND 1),
  production_value REAL,
  expected_surplus REAL,
  risk_flags_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(risk_flags_json)),
  market_artifact_id TEXT REFERENCES artifact_imports(id),
  production_artifact_id TEXT REFERENCES artifact_imports(id),
  owner_profile_artifact_id TEXT REFERENCES artifact_imports(id),
  PRIMARY KEY (draft_id, player_id)
);

CREATE TABLE roster_slots (
  id TEXT PRIMARY KEY,
  team_id TEXT NOT NULL REFERENCES teams(id),
  slot_type TEXT NOT NULL,
  ordinal INTEGER NOT NULL CHECK (ordinal > 0),
  eligible_positions_json TEXT NOT NULL CHECK (json_valid(eligible_positions_json)),
  player_id TEXT REFERENCES players(id),
  filled_sale_id TEXT,
  UNIQUE (team_id, slot_type, ordinal),
  UNIQUE (team_id, player_id)
);

CREATE TABLE draft_events (
  id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  sequence INTEGER NOT NULL CHECK (sequence > 0),
  event_type TEXT NOT NULL CHECK (event_type IN (
    'draft_created','draft_started','nomination_opened','nomination_cancelled',
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

CREATE TRIGGER draft_events_no_update
BEFORE UPDATE ON draft_events BEGIN SELECT RAISE(ABORT, 'draft events are immutable'); END;
CREATE TRIGGER draft_events_no_delete
BEFORE DELETE ON draft_events BEGIN SELECT RAISE(ABORT, 'draft events are immutable'); END;

CREATE TABLE nominations (
  id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  player_id TEXT NOT NULL REFERENCES players(id),
  nominated_by_team_id TEXT REFERENCES teams(id),
  status TEXT NOT NULL CHECK (status IN ('open','sold','cancelled')),
  opened_event_id TEXT NOT NULL REFERENCES draft_events(id),
  closed_event_id TEXT REFERENCES draft_events(id),
  opened_at TEXT NOT NULL,
  closed_at TEXT,
  CHECK ((status = 'open' AND closed_event_id IS NULL AND closed_at IS NULL) OR
         (status <> 'open' AND closed_event_id IS NOT NULL AND closed_at IS NOT NULL))
);
CREATE UNIQUE INDEX one_open_nomination_per_draft ON nominations(draft_id) WHERE status = 'open';
CREATE UNIQUE INDEX one_open_nomination_per_player ON nominations(draft_id, player_id) WHERE status = 'open';

CREATE TABLE sales (
  id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  nomination_id TEXT NOT NULL REFERENCES nominations(id),
  player_id TEXT NOT NULL REFERENCES players(id),
  winner_team_id TEXT NOT NULL REFERENCES teams(id),
  price INTEGER NOT NULL CHECK (price > 0),
  recorded_event_id TEXT NOT NULL REFERENCES draft_events(id),
  roster_slot_id TEXT REFERENCES roster_slots(id),
  voided_event_id TEXT REFERENCES draft_events(id),
  recorded_at TEXT NOT NULL,
  voided_at TEXT,
  CHECK ((voided_event_id IS NULL AND voided_at IS NULL) OR
         (voided_event_id IS NOT NULL AND voided_at IS NOT NULL))
);
CREATE UNIQUE INDEX one_active_sale_per_player ON sales(draft_id, player_id) WHERE voided_event_id IS NULL;
CREATE UNIQUE INDEX one_active_sale_per_nomination ON sales(nomination_id) WHERE voided_event_id IS NULL;

CREATE TABLE sync_outbox (
  id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL REFERENCES drafts(id),
  event_id TEXT NOT NULL REFERENCES draft_events(id),
  destination TEXT NOT NULL CHECK (destination IN ('google_sheets')),
  operation_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','in_flight','succeeded','failed')),
  attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
  payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
  next_attempt_at TEXT,
  last_error TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  succeeded_at TEXT
);
CREATE INDEX pending_sync_work ON sync_outbox(status, next_attempt_at, created_at);
CREATE INDEX events_for_recovery ON draft_events(draft_id, sequence);
CREATE INDEX available_players ON draft_player_pool(draft_id, status);
CREATE INDEX roster_by_team ON roster_slots(team_id, slot_type, ordinal);

INSERT INTO schema_migrations(version, name) VALUES (1, 'initial_offline_draft_domain');
