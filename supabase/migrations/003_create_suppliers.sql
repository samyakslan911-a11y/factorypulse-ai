CREATE TABLE suppliers (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id        UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name           TEXT NOT NULL,
  website        TEXT,
  country        TEXT,
  industry       TEXT,
  contact_email  TEXT,
  notes          TEXT,
  tags           TEXT[] DEFAULT '{}',
  created_at     TIMESTAMPTZ DEFAULT now(),
  deleted_at     TIMESTAMPTZ
);

CREATE INDEX idx_suppliers_user ON suppliers(user_id, deleted_at);
