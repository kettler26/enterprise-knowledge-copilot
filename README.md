# SaaS Support & RevOps Copilot

Production-oriented blueprint for a B2B SaaS AI product that can be monetized:

- Local LLMs with Ollama (`gemma`, `llama`, `mistral`)
- LangGraph orchestration for deterministic agent flows
- Custom RAG + Qdrant (+ optional LlamaIndex experiments via `requirements-llamaindex.txt`)
- MCP tool layer for integrations (Zendesk, HubSpot, Jira, Slack, GitHub)
- Next.js app for agent UI and admin/eval dashboards
- SQLite/DuckDB for local state and analytics
- Langfuse/Phoenix for tracing, evals, and quality monitoring

## Market focus (ICP)

Target customer profile:

- SaaS companies with 20-500 employees
- Support team size: 5-100 agents
- Pain: scattered knowledge base, inconsistent answers, long time-to-resolution
- Buyer: Head of Support / VP CX / COO

Core value proposition:

- Deflect repetitive support requests
- Reduce average handling time (AHT) with grounded, cited answers
- Speed up onboarding for new support reps
- Keep audit trail of model outputs, tools used, and source documents

## Product scope (MVP)

MVP should do only what directly impacts support metrics:

1. Ask internal knowledge questions with source citations
2. Draft support replies from ticket context + documentation
3. Suggest next action (macro/template/escalation), human-approved
4. Log every run with trace IDs and quality signals

Initial integrations (read-first):

- Docs: Notion / Confluence / Markdown folders
- Ticketing: Zendesk or Intercom (read first, write in phase 2)
- Chat/context: Slack channel history (optional)

## Technical architecture

- `apps/web`: Next.js portal
  - agent chat UI
  - support copilot panel
  - admin settings + eval dashboard
- `apps/api`: FastAPI service
  - LangGraph workflows
  - LlamaIndex ingestion/retrieval
  - model routing for Ollama
- `packages/mcp-servers`: MCP adapters for external systems
- `data`: local volumes for Qdrant, sqlite, and ingestion cache

## Quick local infra

```bash
docker compose up -d qdrant
# Optional local LLM and observability:
docker compose --profile llm --profile observability up -d
```

Ollama endpoint: `http://localhost:11434`
Qdrant endpoint: `http://localhost:6333`
Phoenix UI: `http://localhost:6006` (if enabled)

## Monetization model

Pricing strategy for SaaS market entry:

- Starter: EUR 499-999/month per workspace
- Growth: EUR 1,500-3,500/month with more integrations + analytics
- Add-ons: SSO, custom connectors, dedicated environment, SLA
- Services: one-time onboarding/integration package (EUR 3k-15k)

Pricing anchor is ROI, not tokens:

- support deflection rate
- AHT improvement
- first-response time reduction
- onboarding time reduction for new agents

## 90-day execution plan

Day 0-30:

- ship ingestion + RAG with citations
- integrate one ticketing source (read-only)
- launch trace dashboard and eval set

Day 31-60:

- add response drafting with agent assist
- implement role-based access and prompt guardrails
- instrument KPI reporting from production logs

Day 61-90:

- add controlled write actions (ticket update/macro apply)
- launch billing + workspace plans
- onboard 3-5 pilot SaaS customers

## Success criteria

Technical:

- p95 response latency under 4 seconds for cached/short queries
- grounded answer rate above 85 percent on eval set
- zero-secrets policy and full traceability for agent actions

Business:

- 3 paid pilots
- measurable deflection and AHT gains within first month of rollout
- first repeatable case study with before/after metrics

## Run the MVP locally

### Without Docker (API + static UI only)

From the repo root:

```powershell
cd enterprise-knowledge-copilot
powershell -ExecutionPolicy Bypass -File .\start-local.ps1
```

Or manually:

```powershell
cd apps\api
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Then open **http://127.0.0.1:8000/ui/** in the browser. If you changed the code and still get **404 on `/ui/`**, stop the old `uvicorn` process and start again so the static mount is loaded.

1. Start core services:

```bash
docker compose up -d qdrant api web
```

2. Start optional local LLM service:

```bash
docker compose --profile llm up -d ollama
```

3. Pull local models (if using Ollama):

```bash
ollama pull mistral-small:latest
ollama pull nomic-embed-text
```

The chat model answers questions; the embedding model powers Qdrant semantic retrieval.

4. Open the app:

- **Web UI (Next.js, optional):** `http://localhost:3000` — requires `npm install` in `apps/web` (on Windows, delete a broken `node_modules` and retry; see Troubleshooting).
- **Web UI (no Node, always works):** `http://localhost:8000/` → redirects to `http://localhost:8000/ui/` (static page served by FastAPI).
- API health: `http://localhost:8000/health`
- Qdrant: `http://localhost:6333`

### Troubleshooting: Next.js / npm on Windows

If `npm install` fails with `ENOTEMPTY`, `TAR_ENTRY_ERROR`, or hangs, close tools that lock `node_modules` (IDE, antivirus scan), then run `npm run clean` in `apps/web` and `npm install` again. You can still use the UI at `http://localhost:8000/ui/` without Node.

SQLite stores full documents and run logs at `APP_DB_PATH`. In Docker Compose the API uses volume `api_data` mounted at `/data` with `APP_DB_PATH=/data/copilot.db`. For local `uvicorn` without Docker, the default file is `copilot.db` in the API process working directory.

Semantic retrieval uses **Qdrant** plus **Ollama embeddings** (`OLLAMA_EMBED_MODEL`, default `nomic-embed-text`). If Ollama or Qdrant is unavailable, ingest still writes to SQLite and chat falls back to keyword search over stored documents.

Chat flow is implemented as **LangGraph**: `retrieve` (RAG) → `generate` (Ollama) → `persist` (SQLite run log). Tune citation volume with `RAG_MIN_VECTOR_SCORE`, `RAG_MAX_CITATIONS`, `RAG_MAX_VECTOR`, and `RAG_MAX_KEYWORD` (see `.env.example`).

## Minimal validation checks

API health:

```bash
curl http://localhost:8000/health
```

Chat request:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"workspace_id\":\"default\",\"message\":\"Draft a concise reply for a billing issue\",\"context\":\"Policy: refund within 14 days for annual plans.\"}"
```

Ingest one knowledge document:

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d "{\"workspace_id\":\"default\",\"source\":\"refund_policy\",\"content\":\"Annual plans can be refunded within 14 days from purchase date.\"}"
```

Read metrics summary:

```bash
curl "http://localhost:8000/metrics/summary?workspace_id=default"
```

Capabilities (feature flags):

```bash
curl http://localhost:8000/capabilities
```

KB search tool (vector retrieval for agents):

```bash
curl -X POST http://localhost:8000/tools/kb-search \
  -H "Content-Type: application/json" \
  -d "{\"workspace_id\":\"default\",\"query\":\"refund policy\",\"limit\":5}"
```

Expected behavior:

- API returns a non-empty `answer`
- `grounded=true` and at least one citation when context is included
- API returns `trace_id` for auditability
- metrics endpoint reports SQLite + DuckDB rollups per workspace
- Web UI can submit and display answer

## Implementation roadmap (status)

### Phase 1 — MVP core (done)

- [x] FastAPI: chat, ingest, metrics, static UI (`/ui/`), health
- [x] SQLite: documents + run audit log
- [x] Qdrant + Ollama embeddings: semantic retrieval + keyword fallback
- [x] LangGraph: `retrieve` → `generate` → `persist`
- [x] DuckDB: analytics mirror + 7-day rollups in `/metrics/summary`
- [x] Optional Langfuse traces (env keys) + optional OTLP → Phoenix
- [x] HTTP tool: `POST /tools/kb-search` for agent/MCP-style integrations
- [x] `GET /capabilities` for ops smoke tests

### Phase 2 — Product hardening (partial / next)

- [ ] Multi-tenant auth (API keys / JWT), workspace isolation beyond string IDs
- [ ] Billing meters + plan enforcement
- [ ] Curated eval dataset + regression tests on `/chat`
- [ ] First-party connectors (Zendesk / Notion read-only) behind feature flags
- [ ] Stdio MCP server wrapping HTTP tools (optional; HTTP bridge exists)

### Phase 3 — Scale & differentiation

- [ ] LlamaIndex path (optional install: `requirements-llamaindex.txt`) for advanced retrieval experiments
- [ ] Streamlit or internal admin dashboards (Next.js remains primary UI)
- [ ] Cloudflare Workers / Hugging Face Spaces deployment templates

## Next build items (production hardening)

- Add tenant isolation and role-based access checks
- Add LlamaIndex-backed retrieval path (optional dependency pack)
- Add billing events and plan enforcement for paid workspaces
- Add stdio MCP server (thin wrapper) once connector scope is fixed

## Commercial execution docs

- GTM pilot playbook: `docs/GTM-Pilot-Playbook.md`
- Pilot statement of work template: `docs/Pilot-Statement-of-Work.md`
- ROI calculator worksheet: `docs/ROI-Calculator.md`
- Discovery call script: `docs/Discovery-Call-Script.md`
