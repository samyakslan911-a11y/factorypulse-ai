# FactoryPulse AI — Supplier Agent Design Spec
**Fecha:** 2026-07-15  
**Estado:** COMPLETO — todas las secciones aprobadas  
**Autor:** Karla  
**Stack:** Python FastAPI + Next.js 15 + Supabase + Claude/Gemini API + Firecrawl

---

## Contexto del proyecto

Plataforma de inteligencia de riesgo de proveedores industriales. Primer módulo de FactoryPulse AI. Diseñado para portafolio de AI Engineering — demuestra: agentes LLM, RAG, pipelines de datos, evaluación, observabilidad.

**Problema que resuelve:** Las pymes latinoamericanas gestionan riesgo de proveedores en Excel. Las herramientas profesionales (SAP Ariba, Coupa) cuestan $30K-$500K/año. FactoryPulse democratiza esa capacidad con IA.

---

## Decisiones de diseño tomadas

| Decisión | Elección | Motivo |
|---|---|---|
| Input de proveedores | Formulario manual + CSV | Cubre ambos flujos reales |
| Tipos de riesgo | Financiero + Operacional + Reputacional | Score compuesto configurable |
| Output | Dashboard web + email de alerta | Cobertura completa |
| Frecuencia análisis | Automático semanal + on-demand | Máxima flexibilidad |
| Arquitectura agente | Claude/Gemini API + tools | AI Engineering real, no pipeline simple |
| LLM desarrollo | Gemini 2.0 Flash (gratis) | Sin costo en desarrollo |
| LLM producción | Claude Sonnet 4.6 | Mejor calidad para demos |
| Diseño multi-LLM | Variable de entorno `LLM_PROVIDER` | Portafolio muestra flexibilidad |

---

## Arquitectura General (Sección 1 — Aprobada)

```
FRONTEND (Next.js 15 + TypeScript + Tailwind)
  /dashboard        → tabla proveedores + scores
  /suppliers/new    → formulario agregar
  /suppliers/import → carga CSV
  /suppliers/[id]   → detalle + historial

BACKEND (Python 3.11 + FastAPI)
  POST /suppliers
  POST /suppliers/import
  POST /suppliers/{id}/analyze
  GET  /suppliers
  GET  /suppliers/{id}/history

SUPPLIER AGENT (Claude/Gemini + 4 tools)
  scrape_website(url)      → Firecrawl
  search_news(company)     → Firecrawl
  search_legal(company)    → Firecrawl
  save_analysis(result)    → Supabase

SUPABASE (PostgreSQL + pgvector)
EMAIL (Resend — 3000/mes gratis)
SCHEDULER (APScheduler dentro de FastAPI)
DEPLOY (Railway)
```

---

## Modelo de Datos (Sección 2 — Aprobada y corregida)

### Tablas

**`users`** — Autenticación básica
```sql
id UUID PK | email TEXT UNIQUE | name TEXT | created_at | deleted_at
```

**`score_config`** — Pesos configurables por usuario (1 por usuario)
```sql
id UUID PK | user_id FK | weight_financial FLOAT DEFAULT 0.40
weight_operational FLOAT DEFAULT 0.40 | weight_reputational FLOAT DEFAULT 0.20
alert_threshold INTEGER DEFAULT 20 | alert_emails TEXT[]
CONSTRAINT weights_sum CHECK (weight_financial + weight_operational + weight_reputational = 1.0)
```

**`suppliers`** — Sin scores (se calculan via vista)
```sql
id UUID PK | user_id FK | name TEXT | website TEXT | country TEXT
industry TEXT | contact_email TEXT | notes TEXT | tags TEXT[]
created_at | deleted_at (soft delete)
```

**`scheduler_runs`** — Trazabilidad del scheduler semanal
```sql
id UUID PK | user_id FK | triggered_by TEXT | started_at | finished_at
suppliers_total INT | suppliers_ok INT | suppliers_failed INT | status TEXT
```

**`analyses`** — Corazón del sistema, cada análisis individual
```sql
id UUID PK | supplier_id FK | user_id FK | scheduler_run_id FK (nullable)
triggered_by TEXT | started_at | finished_at | status TEXT | error_message TEXT
model_used TEXT | tokens_input INT | tokens_output INT
score_total INT | score_financial INT | score_operational INT | score_reputational INT
score_delta INT | weight_financial_used FLOAT | weight_operational_used FLOAT
weight_reputational_used FLOAT | summary TEXT | findings JSONB | sources_used JSONB
```

**`alerts`** — Una o más por análisis
```sql
id UUID PK | supplier_id FK | analysis_id FK | user_id FK
type TEXT | severity TEXT | message TEXT | score_before INT | score_after INT
channel TEXT | recipients TEXT[] | sent_at | send_status TEXT
acknowledged BOOL | acknowledged_at | acknowledged_by FK
```

**`supplier_embeddings`** — Búsqueda semántica (pgvector)
```sql
id UUID PK | supplier_id FK | analysis_id FK | chunk_index INT
content_type TEXT | content TEXT | embedding_model TEXT DEFAULT 'text-embedding-004'
embedding VECTOR(768) | created_at
```

**`analysis_steps`** — Observabilidad: trazabilidad de cada paso del agente
```sql
id UUID PK | analysis_id FK | step_number INT | tool_used TEXT
tool_input JSONB | tool_output_summary TEXT | tokens_used INT | duration_ms INT | created_at
```

### Vista principal
```sql
CREATE VIEW suppliers_view AS
SELECT s.*, a.score_total AS current_score, a.score_financial,
       a.score_operational, a.score_reputational, a.score_delta,
       a.finished_at AS last_analyzed, a.status AS last_analysis_status,
       CASE WHEN a.score_total >= 70 THEN 'critical'
            WHEN a.score_total >= 40 THEN 'watch'
            WHEN a.score_total IS NULL THEN 'pending'
            ELSE 'active' END AS risk_status
FROM suppliers s
LEFT JOIN analyses a ON a.id = (
  SELECT id FROM analyses WHERE supplier_id = s.id AND status = 'done'
  ORDER BY created_at DESC LIMIT 1
)
WHERE s.deleted_at IS NULL;
```

---

## Diseño del Agente (Sección 3 — Aprobada)

### Patrón: Agent Loop
```
THINK → ACT (tool) → OBSERVE → THINK → ... → save_analysis() → END
```

### 4 Herramientas
1. `scrape_website(url)` → lee sitio web del proveedor via Firecrawl
2. `search_news(company_name, country)` → busca noticias recientes
3. `search_legal(company_name)` → busca demandas y registros regulatorios
4. `save_analysis(scores, summary, findings)` → forced termination tool, guarda en Supabase

### System Prompt (resumen)
- Rol: analista senior de riesgo con 15 años de experiencia
- Metodología: web → noticias → legal → save (siempre en ese orden mínimo)
- Scoring con rúbricas explícitas por rango (0-20, 21-50, 51-75, 76-100) para cada categoría
- Sin hallazgos sin evidencia — si no hay fuente, se dice explícitamente

### Observabilidad (AgentObserver)
- Cada tool call se registra en `analysis_steps` (input, output_summary, tokens, duration_ms)
- Permite replay completo del razonamiento del agente
- Base para debugging y mejora continua

### Evaluación (Evals)
```python
# 3 métricas automáticas post-análisis:
coverage_ok   = len(sources_used) >= 3       # usó suficientes fuentes
grounding_ok  = all findings tienen source_url  # cada hallazgo tiene evidencia
# Si alguna falla → needs_human_review = True → alerta al usuario
```

### Flujo completo
```
POST /analyze → analyses INSERT (running) → cargar score_config
→ Agent Loop (scrape + news + legal + save)
→ evaluate_analysis() → analysis_steps guardados
→ analyses UPDATE (done) → embeddings INSERT
→ score_delta > threshold? → alert INSERT → email Resend
→ suppliers_view se actualiza automáticamente
```

---

## Frontend (Sección 4 — Aprobada)

### 4 Pantallas principales

1. **`/dashboard`** — Tabla de proveedores con score, estado (CRÍTICO/WATCH/ACTIVO/PENDIENTE), delta, última análisis. KPIs arriba: total, críticos, watch, activos.
2. **`/suppliers/[id]`** — Score actual + desglose (financial/operational/reputational), gráfico histórico, hallazgos con evidencia y links, traza del agente expandible.
3. **`/suppliers/new`** — Formulario manual: nombre, web, país, industria, email, notas, tags. Checkbox "analizar al guardar".
4. **`/suppliers/import`** — Drag & drop CSV, vista previa con validación, plantilla descargable.

### Sidebar persistente
AlertCenter visible en todas las páginas — alertas pendientes con badge de cantidad.

### Componentes clave
- `<AnalyzeButton>` — dispara análisis y muestra progreso en tiempo real via SSE
- `<ScoreChart>` — gráfico histórico de scores
- `<FindingCard>` — hallazgo con severity badge, descripción, link a fuente
- `<AgentTrace>` — pasos del agente expandibles (herramienta, duración, tokens)

### Principio de diseño: Explainability
Todo score tiene cadena de evidencia visible: número → hallazgo → fuente → URL.

---

## Estructura de Carpetas (Sección 5 — Aprobada)

```
factorypulse-ai/
├── backend/
│   ├── agent/          # supplier_agent.py, tools.py, prompts.py, observer.py, evaluator.py
│   ├── api/            # suppliers.py, analyses.py, alerts.py, stream.py (SSE)
│   ├── db/             # client.py, suppliers.py, analyses.py, embeddings.py
│   ├── services/       # firecrawl.py, email.py, llm.py (abstracción multi-LLM)
│   ├── scheduler/      # jobs.py (APScheduler)
│   ├── models/         # supplier.py, analysis.py, alert.py (Pydantic)
│   ├── main.py
│   ├── config.py
│   └── requirements.txt
├── frontend/
│   ├── app/            # dashboard/, suppliers/new/, suppliers/import/, suppliers/[id]/
│   ├── components/     # ui/, supplier/, layout/
│   └── lib/            # api.ts, types.ts, utils.ts
├── supabase/
│   └── migrations/     # 001 a 009 — todas las tablas + vista
├── docs/specs/
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## Plan de Implementación (Sección 5 — Aprobada)

| Fase | Días | Al terminar puedes |
|---|---|---|
| 1 — Fundación | 3 | Ver dashboard vacío en browser |
| 2 — Agente Core | 4 | Correr agente desde terminal |
| 3 — API + Frontend | 4 | Analizar proveedor desde la UI |
| 4 — Visualización | 3 | Ver razonamiento del agente en browser |
| 5 — Automatización | 2 | Recibir emails automáticos de alerta |
| 6 — Deploy + Demo | 2 | URL pública + video demo en portafolio |
| **Total** | **~18 días** | **Proyecto completo** |

### Principio AI Engineering: build → eval → iterate
Cada fase termina con algo ejecutable y medible. No avanzar sin confirmar que la fase anterior funciona.
