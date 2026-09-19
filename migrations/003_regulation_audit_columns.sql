ALTER TABLE regulation_versions
  ADD COLUMN IF NOT EXISTS created_by uuid REFERENCES users(id);

CREATE INDEX IF NOT EXISTS idx_regulation_versions_regulation_status
  ON regulation_versions(regulation_id, status);
