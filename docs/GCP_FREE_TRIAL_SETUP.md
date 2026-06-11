# Google Cloud free trial setup (Phase 1)

OpenAid uses **Google ADK** with **Vertex AI** on a **GCP free trial** — no hackathon $100 credits required.

Official hackathon resources: [rapid-agent.devpost.com/resources](https://rapid-agent.devpost.com/resources)

---

## What you get for $0

- [GCP free trial](https://cloud.google.com/free): **$300 credit for 90 days** (new accounts)
- Vertex AI Gemini API calls (covered by trial credits)
- Cloud Run / Secret Manager later (Phase 5) — also within free tier for a demo

You may need a credit card to **verify** the account; Google states you won't be charged if you stay within the free trial.

---

## Step 1 — Create a GCP account and project

1. Go to [cloud.google.com/free](https://cloud.google.com/free) and start the free trial.
2. Open [Google Cloud Console](https://console.cloud.google.com/).
3. Create a project (top bar → **Select project** → **New project**).
4. Note your **Project ID** (e.g. `openaid-provisioner-123`).

---

## Step 2 — Enable APIs

> **May 2026 rename:** Google rebranded **Vertex AI** to **Gemini Enterprise Agent Platform** in the console. The underlying API is unchanged (`aiplatform.googleapis.com`). Your ADK code still works — search for the new name in the console.

In Cloud Console, go to **APIs & Services → Library** and enable:

| Search for this name | API ID | Why |
|---------------------|--------|-----|
| **Vertex AI API** or **Gemini Enterprise Agent Platform API** | `aiplatform.googleapis.com` | Gemini models via ADK |
| **Cloud Run Admin API** | `run.googleapis.com` | Phase 5 deployment |
| **Secret Manager API** | `secretmanager.googleapis.com` | Phase 4–5 secrets |

Or use Cloud Shell / local terminal (replace `YOUR_PROJECT_ID`):

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable aiplatform.googleapis.com run.googleapis.com secretmanager.googleapis.com
```

**Can't find "Vertex AI" in the console?** That's expected after the rebrand. Use **APIs & Services → Library → search `aiplatform`** or run the `gcloud services enable` command above.

---

## Step 3 — Install Google Cloud CLI (Windows)

1. Download: [cloud.google.com/sdk/docs/install](https://cloud.google.com/sdk/docs/install)
2. Run the installer.
3. Open a **new** PowerShell window and run:

```powershell
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud auth application-default login
```

`application-default login` is what the Python backend uses locally (ADC).

---

## Step 4 — Configure `backend/.env`

```env
# Vertex AI via GCP free trial (primary)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
USE_VERTEX_AI=true
GEMINI_MODEL=gemini-2.5-flash

# Optional: AI Studio key for offline fallback only
# GOOGLE_API_KEY=
```

| Variable | Required for Vertex? |
|----------|---------------------|
| `GOOGLE_CLOUD_PROJECT` | **Yes** |
| `GOOGLE_CLOUD_LOCATION` | Yes (default `us-central1`) |
| `USE_VERTEX_AI` | Yes (`true`) |
| `GOOGLE_API_KEY` | No (only if `USE_VERTEX_AI=false`) |

Try `gemini-2.5-flash` first. If your project has Gemini 3, you can set `GEMINI_MODEL=gemini-3-flash-preview`.

---

## Step 5 — Verify Phase 1

From `backend/` with venv activated:

```powershell
.venv\Scripts\activate
python scripts/verify_gcp.py
```

Expected:

```
gemini_backend: vertex
gemini_configured: True
interpret_mission: OK — region=Kenya ...
```

Then start the app:

```powershell
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/health — you should see:

```json
"gemini_backend": "vertex",
"gcp_project": "your-project-id"
```

---

## Step 6 — Stay within free trial (important)

1. In Console → **Billing → Budgets & alerts** → create a **$1 budget alert**.
2. Use **demo mode** (`DEMO_MODE=true`) for daily testing.
3. Delete unused Cloud Run services after Phase 5.
4. Don't leave Fivetran syncs running 24/7 (Phase 2+).

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `403 Permission denied` on Vertex | Enable Vertex AI API; wait 2–5 min |
| `Could not automatically determine credentials` | Run `gcloud auth application-default login` |
| `Project not found` | Check `GOOGLE_CLOUD_PROJECT` matches Project **ID**, not display name |
| `429 Resource exhausted` | Free tier quota; retry or switch model |
| Falls back to regex (no Gemini) | Run `verify_gcp.py`; check `.env` and ADC |

---

## Phase 1 complete when

- [ ] GCP free trial project created
- [ ] Vertex AI API enabled
- [ ] `gcloud auth application-default login` done
- [ ] `GOOGLE_CLOUD_PROJECT` set in `.env`
- [ ] `verify_gcp.py` passes
- [ ] `/health` shows `"gemini_backend": "vertex"`
- [ ] UI mission shows Gemini-derived `hdx_query` in step 1

Then proceed to **Phase 2: Fivetran MCP**.
