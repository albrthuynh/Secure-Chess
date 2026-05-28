BEGIN;

CREATE TABLE IF NOT EXISTS audit_logs (
  audit_id     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type   TEXT        NOT NULL,
  user_id      UUID        REFERENCES users(user_id),  -- nullable: failed logins may not have a user
  ip_address   TEXT,
  metadata     JSONB,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_event_type  ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id     ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at  ON audit_logs(created_at);

-- Enforce append-only at the DB level: block any UPDATE or DELETE on this table.
-- Even if application code had a bug, the database itself would refuse to modify records.
CREATE RULE audit_logs_no_update AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE audit_logs_no_delete AS ON DELETE TO audit_logs DO INSTEAD NOTHING;

COMMIT;
