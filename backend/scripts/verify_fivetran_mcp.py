#!/usr/bin/env python3
"""Verify Fivetran MCP stdio integration (Phase 2).

Usage (from backend/):
  python scripts/verify_fivetran_mcp.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.tools.fivetran_gateway import FivetranGateway
from app.tools.fivetran_mcp_stdio import close_fivetran_mcp, is_fivetran_mcp_available


async def main() -> int:
    print("=== OpenAid Phase 2 — Fivetran MCP check ===\n")
    print(f"fivetran_configured:   {settings.fivetran_configured}")
    print(f"fivetran_use_mcp:      {settings.fivetran_use_mcp}")
    print(f"mcp_available:         {is_fivetran_mcp_available()}")
    print(f"mcp_command:           {settings.fivetran_mcp_command}")
    print(f"mcp_args:              {settings.fivetran_mcp_argv}")
    print()

    if not settings.fivetran_configured:
        print("SKIP: Add FIVETRAN_API_KEY, FIVETRAN_API_SECRET, FIVETRAN_GROUP_ID to .env")
        print("See docs/FIVETRAN_MCP_SETUP.md")
        return 0

    gateway = FivetranGateway()
    try:
        print("Calling list_connections...")
        connections = await gateway.list_connections()
        print(f"  backend: {gateway.last_backend}")
        print(f"  tool:    {gateway.last_tool}")
        print(f"  count:   {len(connections)}")

        print("\nCalling list_metadata_connectors...")
        metadata = await gateway.list_metadata_connectors()
        print(f"  backend: {gateway.last_backend}")
        print(f"  tool:    {gateway.last_tool}")
        print(f"  count:   {len(metadata)}")

        if gateway.last_backend != "mcp":
            print("\nWARN: MCP did not succeed — using REST fallback.")
            print("Install uv (uvx) and ensure FIVETRAN_USE_MCP=true")
            return 1

        print("\nOK — Fivetran MCP is working")
        return 0
    except Exception as exc:
        print(f"\nFAIL: {exc}")
        return 1
    finally:
        await close_fivetran_mcp()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
