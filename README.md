# OpenAid Provisioner

AI provisioning agent for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/) — **Fivetran track**.

Turns vague humanitarian data requests into governed Fivetran pipelines: search HDX sources, choose connector strategy, configure schema policy, sync to BigQuery, and deliver field briefings — with human approval on every write.

## Stack

| Layer | Technology | Status |
|-------|------------|--------|
| Brain | Gemini + Google ADK | **Working** (Phase 1) |
| Superpower | Fivetran MCP | **Working** (Phase 2, needs Fivetran trial creds) |
| Discovery | HDX CKAN API | **Working** |
| Orchestration | FastAPI + SSE | **Working** |
| UX | Next.js dashboard | **Working** |
| Destination | BigQuery via Fivetran | Phase 4 |
| Custom ingest | Connector SDK (`connector-sdk/`) | Template ready |

## Quick start

### Prerequisites

- Python 3.11+
- Node.js 20+
- [GCP free trial](https://cloud.google.com/free) + Vertex AI (**Phase 1** — see [docs/GCP_FREE_TRIAL_SETUP.md](docs/GCP_FREE_TRIAL_SETUP.md))
- [uv](https://docs.astral.sh/uv/) (for Fivetran MCP in Phase 2)
- Fivetran account (14-day trial) — [Phase 2 setup](docs/FIVETRAN_MCP_SETUP.md)
- BigQuery destination in Fivetran (Phase 3+)

### Phase 1 — Google Cloud (free trial)

1. Create a GCP project at [cloud.google.com/free](https://cloud.google.com/free)
2. Enable **Vertex AI API**
3. Run `gcloud auth application-default login`
4. Set in `backend/.env`:
   ```env
   GOOGLE_CLOUD_PROJECT=your-project-id
   USE_VERTEX_AI=true
   ```
5. Verify: `python scripts/verify_gcp.py`

Full walkthrough: **[docs/GCP_FREE_TRIAL_SETUP.md](docs/GCP_FREE_TRIAL_SETUP.md)**

### Phase 2 — Fivetran MCP (free trial)

1. Sign up at [fivetran.com](https://fivetran.com/) (14-day trial)
2. Add API key, secret, group ID to `backend/.env`
3. Install [uv](https://docs.astral.sh/uv/) for `uvx`
4. Verify: `python scripts/verify_fivetran_mcp.py`

Guide: **[docs/FIVETRAN_MCP_SETUP.md](docs/FIVETRAN_MCP_SETUP.md)**

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — add GOOGLE_CLOUD_PROJECT (see GCP guide above)
python scripts/verify_gcp.py
uvicorn app.main:app --reload --port 8000
```

Verify: http://localhost:8000/health (`gemini_backend` should be `"vertex"`)

### 2. Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000

## Demo flow

1. Enter: *"We need latest medical supply data for flooded regions in Kenya — our dashboard is empty."*
2. Watch the agent stream steps: HDX search → gap analysis → connector plan
3. **Approve** the provisioning plan in the UI
4. Agent provisions Fivetran connection (simulated in demo mode)
5. Receive a field briefing summary

## Demo vs live

| Setting | Demo (default) | Live |
|---------|----------------|------|
| `DEMO_MODE` | `true` | `false` |
| `FIVETRAN_ALLOW_WRITES` | `false` | `true` |
| Fivetran provision | Simulated | Real MCP/API calls |
| HDX search | Real API | Real API |
| Gemini reasoning | Vertex AI (GCP trial) | API key fallback |
| BigQuery briefing | Template text | Phase 4+ |

**Local hackathon demo:** leave `DEMO_MODE=true`. Phase 1 needs a **GCP free trial project** (Vertex). Fivetran keys only for Phase 2+.

**Live provisioning:** set `DEMO_MODE=false`, add Fivetran credentials, set `FIVETRAN_ALLOW_WRITES=true` (Phase 3).

## Environment variables

| Variable | Required | Phase | Description |
|----------|----------|-------|-------------|
| `GOOGLE_CLOUD_PROJECT` | Phase 1 | 1 | GCP project ID (free trial) |
| `USE_VERTEX_AI` | Phase 1 | 1 | `true` = Vertex via GCP (recommended) |
| `GOOGLE_API_KEY` | Optional | 1 | AI Studio fallback if `USE_VERTEX_AI=false` |
| `GEMINI_MODEL` | No | 1 | Model ID (default `gemini-2.5-flash`) |
| `FIVETRAN_API_KEY` | Phase 2+ | 2 | Fivetran API key |
| `FIVETRAN_API_SECRET` | Phase 2+ | 2 | Fivetran API secret |
| `FIVETRAN_GROUP_ID` | Phase 2+ | 2 | Destination group ID |
| `FIVETRAN_ALLOW_WRITES` | No | 3 | `true` to allow create/sync (default `false`) |
| `BIGQUERY_PROJECT` | Phase 4 | 4 | GCP project for briefings |
| `BIGQUERY_DATASET` | Phase 4 | 4 | Dataset with synced tables |
| `DEMO_MODE` | No | 0 | `true` simulates Fivetran writes (default) |
| `CORS_ORIGINS` | No | 0 | Frontend origin(s) |
| `NEXT_PUBLIC_API_URL` | No | 0 | Frontend → backend URL |

## Build phases

| Phase | Focus | Status |
|-------|--------|--------|
| **0** | Foundation, config, scaffolds | **Done** |
| **1** | Gemini + ADK reasoning | **Done** |
| **2** | Fivetran MCP stdio | **Done** (add creds + `verify_fivetran_mcp.py`) |
| **3** | Full pipeline lifecycle | **Next** |
| **4** | BigQuery field briefing | Planned |
| **5** | Cloud Run deployment | Planned |
| **6** | Demo video + Devpost | Planned |

## Hackathon submission

- **Track:** Fivetran
- **Hosted URL:** (Phase 5 — Cloud Run + Vercel)
- **License:** MIT

## Project structure

```
openaid-provisioner/
├── backend/
│   └── app/
│       ├── agents/
│       │   ├── orchestrator.py   # 8-step mission + approval gate
│       │   └── adk_agent.py      # ADK scaffold (Phase 1)
│       ├── tools/
│       │   ├── hdx_search.py     # Live HDX API
│       │   ├── fivetran_mcp.py   # Fivetran REST client (MCP in Phase 2)
│       │   ├── gemini_reason.py  # Gemini helpers (Phase 1)
│       │   └── bigquery_briefing.py
│       ├── capabilities.py       # Runtime mode flags
│       ├── config.py
│       └── main.py               # FastAPI + SSE
├── frontend/                     # Next.js operator dashboard
├── connector-sdk/                # HDX CSV/JSON → Fivetran
└── LICENSE
```
