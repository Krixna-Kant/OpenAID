"""Unified Fivetran access: MCP (preferred) with REST fallback."""

from __future__ import annotations

import logging
from typing import Any, Literal

from app.config import settings
from app.tools import fivetran_mcp_stdio as mcp
from app.tools.fivetran_mcp import FivetranClient

logger = logging.getLogger(__name__)

FivetranBackend = Literal["mcp", "rest", "none"]


class FivetranGateway:
    """Route Fivetran reads/writes through MCP when available."""

    def __init__(self) -> None:
        self._rest = FivetranClient()
        self.last_backend: FivetranBackend = "none"
        self.last_tool: str | None = None

    async def list_connections(self) -> list[dict]:
        if mcp.is_fivetran_mcp_available():
            try:
                items = await mcp.list_connections_mcp()
                self.last_backend = "mcp"
                self.last_tool = "fivetran.mcp.list_connections"
                return items
            except Exception as exc:
                logger.warning("Fivetran MCP list_connections failed: %s", exc)

        if settings.fivetran_configured:
            items = await self._rest.list_connections()
            self.last_backend = "rest"
            self.last_tool = "fivetran.rest.list_connections"
            return items

        self.last_backend = "none"
        self.last_tool = None
        return []

    async def list_metadata_connectors(self) -> list[dict]:
        if mcp.is_fivetran_mcp_available():
            try:
                items = await mcp.list_metadata_connectors_mcp()
                self.last_backend = "mcp"
                self.last_tool = "fivetran.mcp.list_metadata_connectors"
                return items
            except Exception as exc:
                logger.warning("Fivetran MCP list_metadata_connectors failed: %s", exc)

        if settings.fivetran_configured:
            items = await self._rest.list_metadata_connectors()
            self.last_backend = "rest"
            self.last_tool = "fivetran.rest.list_metadata_connectors"
            return items

        self.last_backend = "none"
        self.last_tool = None
        return []

    async def create_connection(self, body: dict[str, Any]) -> dict:
        if mcp.is_fivetran_mcp_available() and settings.fivetran_allow_writes:
            try:
                result = await mcp.call_fivetran_mcp_tool("create_connection", body)
                self.last_backend = "mcp"
                self.last_tool = "fivetran.mcp.create_connection"
                if isinstance(result, dict):
                    return result.get("data", result)
                return {"result": result}
            except Exception as exc:
                logger.warning("Fivetran MCP create_connection failed: %s", exc)

        result = await self._rest.create_connection(body)
        self.last_backend = "rest"
        self.last_tool = "fivetran.rest.create_connection"
        return result
