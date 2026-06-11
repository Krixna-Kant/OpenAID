"""Runtime capability flags for health checks and demo vs live mode."""

from __future__ import annotations

from app.config import settings
from app.gcp_runtime import gemini_backend


def get_runtime_capabilities() -> dict[str, bool | str]:
    """Summarize which integrations are configured and active."""
    mode = "demo"
    if not settings.demo_mode and settings.fivetran_allow_writes:
        mode = "live"
    elif not settings.demo_mode:
        mode = "read_only"

    return {
        "mode": mode,
        "demo_mode": settings.demo_mode,
        "gemini_configured": settings.gemini_configured,
        "fivetran_configured": settings.fivetran_configured,
        "fivetran_writes_enabled": settings.fivetran_allow_writes,
        "fivetran_mcp_configured": settings.fivetran_mcp_configured,
        "bigquery_configured": settings.bigquery_configured,
        "hdx_search": True,
        "gemini_backend": gemini_backend(),
        "gemini_uses_vertex": settings.gemini_uses_vertex,
        "gemini_reasoning": settings.gemini_configured,
        "fivetran_mcp_enabled": settings.fivetran_use_mcp,
        "fivetran_mcp_active": settings.fivetran_use_mcp and settings.fivetran_mcp_configured,
        "bigquery_briefing_live": False,  # Phase 4
    }
