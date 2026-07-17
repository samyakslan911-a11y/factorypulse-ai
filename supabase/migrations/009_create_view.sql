CREATE VIEW suppliers_view AS
SELECT
  s.id,
  s.user_id,
  s.name,
  s.website,
  s.country,
  s.industry,
  s.tags,
  s.notes,
  s.created_at,
  a.id              AS last_analysis_id,
  a.score_total     AS current_score,
  a.score_financial,
  a.score_operational,
  a.score_reputational,
  a.score_delta,
  a.finished_at     AS last_analyzed,
  a.status          AS last_analysis_status,
  a.model_used      AS last_model_used,
  CASE
    WHEN a.score_total >= 70 THEN 'critical'
    WHEN a.score_total >= 40 THEN 'watch'
    WHEN a.score_total IS NULL THEN 'pending'
    ELSE 'active'
  END AS risk_status
FROM suppliers s
LEFT JOIN analyses a ON a.id = (
  SELECT id FROM analyses
  WHERE supplier_id = s.id
    AND status = 'done'
  ORDER BY started_at DESC
  LIMIT 1
)
WHERE s.deleted_at IS NULL;
