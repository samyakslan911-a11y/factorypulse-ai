CREATE TABLE analysis_steps (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  analysis_id          UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  step_number          INTEGER NOT NULL,
  tool_used            TEXT NOT NULL,
  tool_input           JSONB,
  tool_output_summary  TEXT,
  tokens_used          INTEGER,
  duration_ms          INTEGER,
  created_at           TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_steps_analysis ON analysis_steps(analysis_id, step_number);
