# Fivetran MCP setup (Phase 2)

OpenAid uses the official [fivetran/fivetran-mcp](https://github.com/fivetran/fivetran-mcp) server via **stdio**, integrated through **Google ADK**'s MCP session manager.

Hackathon track: **Fivetran** — partner MCP is required.

---

## Prerequisites

1. [Fivetran account](https://fivetran.com/) — **14-day free trial** is enough for the hackathon
2. [uv](https://docs.astral.sh/uv/) installed (`uvx` command available)
3. API credentials from [Fivetran dashboard → API Config](https://fivetran.com/dashboard/user/api-config)

---

## Step 1 — Get Fivetran credentials

| Value | Where |
|-------|--------|
| `FIVETRAN_API_KEY` | API Config page |
| `FIVETRAN_API_SECRET` | API Config page |
| `FIVETRAN_GROUP_ID` | Destination group ID in Fivetran dashboard URL or API |

---

## Step 2 — Configure `backend/.env`

```env
FIVETRAN_API_KEY=your_key
FIVETRAN_API_SECRET=your_secret
FIVETRAN_GROUP_ID=your_group_id
FIVETRAN_ALLOW_WRITES=false
FIVETRAN_USE_MCP=true
```

Keep `FIVETRAN_ALLOW_WRITES=false` until you intentionally test live provisioning (Phase 3).

---

## Step 3 — Verify MCP connection

```powershell
cd backend
.venv\Scripts\activate
python scripts/verify_fivetran_mcp.py
```

Expected:

```
backend: mcp
list_connections: OK (N connections)
list_metadata_connectors: OK (M connector types)
```

---

## How it works in OpenAid

| Mission step | MCP tool | Fallback |
|--------------|----------|----------|
| Gap analysis | `list_connections` | Fivetran REST |
| Connector strategy | `list_metadata_connectors` | Fivetran REST |
| Provision (live) | `create_connection` | REST (Phase 3) |

The UI step stream shows tool names like `fivetran.mcp.list_connections` when MCP is active.

ADK `McpToolset` is defined in `app/agents/fivetran_adk_tools.py` for agent-level tool use.

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `uvx` not found | Install uv: `pip install uv` or [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| MCP spawn timeout | First `uvx` run downloads the server — wait up to 2 min; increase `FIVETRAN_MCP_TIMEOUT` |
| 401 from Fivetran | Check API key/secret |
| Falls back to REST | MCP failed; check logs; mission still runs if REST works |
| Disable MCP | `FIVETRAN_USE_MCP=false` |

---

## Phase 2 complete when

- [ ] Fivetran trial credentials in `.env`
- [ ] `uv` / `uvx` installed
- [ ] `verify_fivetran_mcp.py` passes
- [ ] Mission step 3 payload shows `"backend": "mcp"`

Then proceed to **Phase 3: full pipeline lifecycle**.
