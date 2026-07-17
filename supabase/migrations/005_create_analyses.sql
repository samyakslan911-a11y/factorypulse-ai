CREATE TABLE analyses (
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id               UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
  user_id                   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  scheduler_run_id          UUID REFERENCES scheduler_runs(id),

  -- Trazabilidad
  triggered_by              TEXT NOT NULL CHECK (triggered_by IN ('scheduled', 'manual')),
  started_at                TIMESTAMPTZ DEFAULT now(),
  finished_at               TIMESTAMPTZ,
  status                    TEXT NOT NULL DEFAULT 'running'
                            CHECK (status IN ('running', 'done', 'failed')),
  error_message             TEXT,
  model_used                TEXT,
  tokens_input              INTEGER,
  tokens_output             INTEGER,

  -- Scores
  score_total               INTEGER CHECK (score_total BETWEEN 0 AND 100),
  score_financial           INTEGER CHECK (score_financial BETWEEN 0 AND 100),
  score_operational         INTEGER CHECK (score_operational BETWEEN 0 AND 100),
  score_reputational        INTEGER CHECK (score_reputational BETWEEN 0 AND 100),
  score_delta               INTEGER,

  -- Pesos usados en este análisis (snapshot de score_config)
  weight_financial_used     FLOAT,
  weight_operational_used   FLOAT,
  weight_reputational_used  FLOAT,

  -- Contenido generado por el agente
  summary                   TEXT,
  findings                  JSONB DEFAULT '[]',
  sources_used              JSONB DEFAULT '[]'
);

CREATE INDEX idx_analyses_supplier ON analyses(supplier_id, started_at DESC);
CREATE INDEX idx_analyses_status   ON analyses(status);
