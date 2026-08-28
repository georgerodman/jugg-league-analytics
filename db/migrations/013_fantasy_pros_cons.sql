ALTER TABLE fantasy_player_summaries ADD COLUMN pros_summary TEXT;
ALTER TABLE fantasy_player_summaries ADD COLUMN cons_summary TEXT;

INSERT INTO schema_migrations(version, name) VALUES (13, 'fantasy_pros_cons');
