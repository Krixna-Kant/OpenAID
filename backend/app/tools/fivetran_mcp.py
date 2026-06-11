"""Fivetran REST API client (read + gated writes).

Phase 2 adds a separate MCP stdio client; this module remains for:
  - Deterministic demo flows when MCP subprocess is unavailable
  - Read-only gap analysis before MCP is wired
  - Cloud Run fallback if MCP stdio is impractical in container

Credentials match the official fivetran/fivetran-mcp server env vars.
"""

from __future__ import annotations

import base64
from typing import Any

import httpx

from app.config import settings

FIVETRAN_BASE = "https://api.fivetran.com/v1"


class FivetranClient:
    def __init__(self) -> None:
        token = base64.b64encode(
            f"{settings.fivetran_api_key}:{settings.fivetran_api_secret}".encode()
        ).decode()
        self._headers = {
            "Authorization": f"Basic {token}",
            "Content-Type": "application/json",
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict:
        if method.upper() in {"POST", "PATCH", "DELETE"} and not settings.fivetran_allow_writes:
            raise PermissionError(
                "Fivetran writes disabled. Set FIVETRAN_ALLOW_WRITES=true after review."
            )
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method, f"{FIVETRAN_BASE}{path}", headers=self._headers, **kwargs
            )
            response.raise_for_status()
            return response.json()

    async def list_connections(self) -> list[dict]:
        data = await self._request("GET", "/connections")
        return data.get("data", {}).get("items", [])

    async def list_metadata_connectors(self) -> list[dict]:
        data = await self._request("GET", "/metadata/connectors")
        return data.get("data", {}).get("items", [])

    async def get_connection_details(self, connection_id: str) -> dict:
        data = await self._request("GET", f"/connections/{connection_id}")
        return data.get("data", {})

    async def create_connection(self, body: dict) -> dict:
        data = await self._request("POST", "/connections", json=body)
        return data.get("data", {})

    async def reload_schema(self, connection_id: str) -> dict:
        data = await self._request("POST", f"/connections/{connection_id}/schemas/reload")
        return data.get("data", {})

    async def modify_schema(self, connection_id: str, schema_body: dict) -> dict:
        data = await self._request(
            "PATCH", f"/connections/{connection_id}/schemas", json=schema_body
        )
        return data.get("data", {})

    async def sync_connection(self, connection_id: str, force: bool = False) -> dict:
        data = await self._request(
            "POST", f"/connections/{connection_id}/force", json={"force": force}
        )
        return data.get("data", {})

    async def run_setup_tests(self, connection_id: str) -> dict:
        data = await self._request("POST", f"/connections/{connection_id}/test")
        return data.get("data", {})
