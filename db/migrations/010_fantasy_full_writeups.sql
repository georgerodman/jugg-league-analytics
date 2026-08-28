ALTER TABLE fantasy_player_summaries ADD COLUMN full_writeup TEXT;

INSERT INTO schema_migrations(version, name) VALUES (10, 'fantasy_full_writeups');
