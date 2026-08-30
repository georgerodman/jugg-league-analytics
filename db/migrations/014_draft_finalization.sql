ALTER TABLE drafts ADD COLUMN finalized_at TEXT;
ALTER TABLE drafts ADD COLUMN finalized_backup_path TEXT;
ALTER TABLE drafts ADD COLUMN google_sheets_sync_enabled INTEGER NOT NULL DEFAULT 1 CHECK (google_sheets_sync_enabled IN (0,1));

INSERT INTO schema_migrations(version, name) VALUES (14, 'draft_finalization_and_sheet_disconnect');
