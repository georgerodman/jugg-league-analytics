ALTER TABLE fantasy_analysis_sources ADD COLUMN source_summary TEXT;

INSERT INTO schema_migrations(version, name) VALUES(7, 'fantasy_analysis_source_summary');
