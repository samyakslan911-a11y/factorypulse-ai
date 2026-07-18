# FactoryPulse AI

**Supplier risk intelligence platform powered by autonomous AI agents.**

Live demo → [factorypulse-ai-3skn.vercel.app](https://factorypulse-ai-3skn.vercel.app)

---

## What it does

FactoryPulse AI monitors your supplier network for financial, operational, and reputational risk. For each supplier, an autonomous agent scrapes their website, searches for recent news and legal actions, synthesizes the findings, and produces a structured risk score — all without human intervention.

The scheduler re-runs analysis every 7 days so your risk picture stays current.

---

## Architecture

```
Browser → Vercel (Next.js 14)
             ↓ direct CORS calls
          Railway (FastAPI + APScheduler)
             ↓
          Supabase (PostgreSQL + pgvector)
             ↓
          Gemini 2.5 Flash (agentic loop)
```

**Agent loop** — 4 tools in sequence:

| Tool | What it does |
|---|---|
| `scrape_website` | Fetches and parses the supplier's public website |
| `search_news` | Queries recent news for the company name |
| `search_legal` | Looks for litigation, sanctions, regulatory actions |
| `save_analysis` | Persists scores and findings to Supabase |

Results stream to the UI in real time via Server-Sent Events (SSE).

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), Tailwind CSS |
| Backend | Python 3.11, FastAPI |
| AI | Google Gemini 2.5 Flash — function calling |
| Database | Supabase (PostgreSQL) |
| Scheduling | APScheduler — periodic re-analysis every 7 days |
| Storage | Cloudflare R2 (optional) |
| Deploy | Railway (backend), Vercel (frontend) |

---

## Features

- **Autonomous risk scoring** — 0–100 score across financial, operational, and reputational dimensions
- **Real-time SSE streaming** — watch the agent work step by step in the UI
- **Automatic re-analysis** — APScheduler triggers fresh analysis for any supplier not seen in 7 days
- **Finding severity tracking** — low / medium / high findings with type and description
- **Analysis history** — full audit trail per supplier with agent steps and timing
- **Demo fallback** — graceful degradation when the AI provider is unavailable

---

## Running locally

**Prerequisites:** Python 3.11+, Node.js 18+, a Supabase project, a Gemini API key.

```bash
# 1. Clone
git clone https://github.com/samyakslan911-a11y/factorypulse-ai.git
cd factorypulse-ai

# 2. Environment
cp .env.example .env
# Fill in SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY

# 3. Backend
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 8000

# 4. Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Database migrations

Migrations live in `supabase/migrations/`. Apply them in order via the Supabase CLI or the SQL editor in the Supabase dashboard.

---

## Environment variables

| Variable | Where | Description |
|---|---|---|
| `SUPABASE_URL` | Backend | Supabase project URL |
| `SUPABASE_KEY` | Backend | Supabase service role key |
| `GEMINI_API_KEY` | Backend | Google AI Studio API key |
| `LLM_PROVIDER` | Backend | `gemini` (default) |
| `SCHEDULER_ENABLED` | Backend | `true` / `false` |
| `SCHEDULER_INTERVAL_DAYS` | Backend | Days between re-analyses (default: 7) |
| `NEXT_PUBLIC_API_URL` | Frontend | Railway backend URL |

---

## Project structure

```
backend/
  agent/          → Gemini agentic loop + tools
  api/            → FastAPI routers (suppliers, analyses, stream, scheduler)
  db/             → Supabase queries
  scheduler/      → APScheduler setup
  config.py       → Pydantic settings
  main.py         → FastAPI app + lifespan

frontend/
  src/app/        → Next.js App Router pages
  src/components/ → SupplierCard, NewSupplierModal, SchedulerWidget
  src/lib/api.ts  → API URL helper

supabase/
  migrations/     → SQL migrations (9 applied)
```

---

## Roadmap

- [ ] User authentication (Supabase Auth)
- [ ] Email alerts via Resend when risk score changes significantly
- [ ] Bulk CSV import of supplier lists
- [ ] PDF export of risk reports
