"""Fivetran partner MCP client (stdio) via Google ADK session manager.

Spawns the official server:
  uvx --from git+https://github.com/fivetran/fivetran-mcp fivetran-mcp

See docs/FIVETRAN_MCP_SETUP.md
"""

from __future__ import annotations

import json
import logging
from typing import Any

from google.adk.tools.mcp_tool.mcp_session_manager import MCPSessionManager
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from app.config import settings

logger = logging.getLogger(__name__)

_manager: MCPSessionManager | None = None


def _fivetran_mcp_env() -> dict[str, str]:
    return {
        "FIVETRAN_API_KEY": settings.fivetran_api_key,
        "FIVETRAN_API_SECRET": settings.fivetran_api_secret,
        "FIVETRAN_ALLOW_WRITES": "true" if settings.fivetran_allow_writes else "false",
    }


def _get_manager() -> MCPSessionManager:
    global _manager
    if _manager is None:
        _manager = MCPSessionManager(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=settings.fivetran_mcp_command,
                    args=settings.fivetran_mcp_argv,
                    env=_fivetran_mcp_env(),
                ),
                timeout=settings.fivetran_mcp_timeout,
            ),
        )
    return _manager


def is_fivetran_mcp_available() -> bool:
    return settings.fivetran_use_mcp and settings.fivetran_mcp_configured


def _parse_mcp_payload(response: Any) -> Any:
    """Extract JSON payload from an MCP CallToolResult."""
    if hasattr(response, "model_dump"):
        dumped = response.model_dump(exclude_none=True, mode="json")
    elif isinstance(response, dict):
        dumped = response
    else:
        return response

    if dumped.get("isError"):
        message = dumped.get("content") or dumped
        raise RuntimeError(f"Fivetran MCP tool error: {message}")

    for block in dumped.get("content") or []:
        if not isinstance(block, dict):
            continue
        text = block.get("text")
        if not text:
            continue
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}

    return dumped


def _normalize_items(payload: Any, items_key: str = "items") -> list[dict]:
    """Normalize Fivetran list_* tool responses to a list of dicts."""
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []

    data = payload.get("data", payload)
    if isinstance(data, dict):
        items = data.get(items_key) or data.get("items")
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    return []


async def call_fivetran_mcp_tool(tool_name: str, arguments: dict[str, Any] | None = None) -> Any:
    """Invoke a Fivetran MCP tool by name."""
    if not is_fivetran_mcp_available():
        raise RuntimeError("Fivetran MCP is not configured")

    manager = _get_manager()
    session = await manager.create_session()
    response = await session.call_tool(tool_name, arguments=arguments or {})
    return _parse_mcp_payload(response)


async def list_connections_mcp() -> list[dict]:
    payload = await call_fivetran_mcp_tool("list_connections", {})
    return _normalize_items(payload)


async def list_metadata_connectors_mcp() -> list[dict]:
    payload = await call_fivetran_mcp_tool("list_metadata_connectors", {})
    return _normalize_items(payload)


async def close_fivetran_mcp() -> None:
    global _manager
    if _manager is not None:
        try:
            await _manager.close()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Fivetran MCP shutdown: %s", exc)
        _manager = None
