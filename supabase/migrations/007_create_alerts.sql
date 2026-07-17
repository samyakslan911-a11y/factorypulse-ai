CREATE TABLE alerts (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id      UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
  analysis_id      UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  user_id          UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type             TEXT NOT NULL CHECK (type IN ('score_increase', 'critical_finding', 'new_critical_supplier')),
  severity         TEXT NOT NULL CHECK (severity IN ('medium', 'high', 'critical')),
  message          TEXT NOT NULL,
  score_before     INTEGER,
  score_after      INTEGER,
  channel          TEXT NOT NULL DEFAULT 'email',
  recipients       TEXT[] NOT NULL DEFAULT '{}',
  sent_at          TIMESTAMPTZ,
  send_status      TEXT NOT NULL DEFAULT 'pending' CHECK (send_status IN ('pending', 'sent', 'failed')),
  acknowledged     BOOLEAN DEFAULT false,
  acknowledged_at  TIMESTAMPTZ,
  acknowledged_by  UUID REFERENCES users(id),
  created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_alerts_user_unread ON alerts(user_id, acknowledged);
