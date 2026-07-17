CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE supplier_embeddings (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_id      UUID NOT NULL REFERENCES suppliers(id) ON DELETE CASCADE,
  analysis_id      UUID NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
  chunk_index      INTEGER NOT NULL DEFAULT 0,
  content_type     TEXT NOT NULL CHECK (content_type IN ('summary', 'findings', 'raw_scrape')),
  content          TEXT NOT NULL,
  embedding_model  TEXT NOT NULL DEFAULT 'text-embedding-004',
  embedding        VECTOR(768),
  created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_embeddings_supplier ON supplier_embeddings(supplier_id);
