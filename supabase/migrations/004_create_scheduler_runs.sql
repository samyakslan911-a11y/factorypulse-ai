CREATE TABLE scheduler_runs (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id            UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  triggered_by       TEXT NOT NULL CHECK (triggered_by IN ('scheduler', 'manual_bulk')),
  started_at         TIMESTAMPTZ DEFAULT now(),
  finished_at        TIMESTAMPTZ,
  suppliers_total    INTEGER DEFAULT 0,
  suppliers_ok       INTEGER DEFAULT 0,
  suppliers_failed   INTEGER DEFAULT 0,
  status             TEXT NOT NULL DEFAULT 'running'
                     CHECK (status IN ('running', 'done', 'partial', 'failed'))
);
