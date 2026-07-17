CREATE TABLE score_config (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id               UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  weight_financial      FLOAT NOT NULL DEFAULT 0.40,
  weight_operational    FLOAT NOT NULL DEFAULT 0.40,
  weight_reputational   FLOAT NOT NULL DEFAULT 0.20,
  alert_threshold       INTEGER NOT NULL DEFAULT 20,
  alert_emails          TEXT[] NOT NULL DEFAULT '{}',
  updated_at            TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id),
  CONSTRAINT weights_sum CHECK (
    ROUND((weight_financial + weight_operational + weight_reputational)::NUMERIC, 2) = 1.00
  )
);
