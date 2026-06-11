"""ADK McpToolset for Fivetran — partner MCP integration for agents."""

from __future__ import annotations

from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from app.config import settings


def create_fivetran_mcp_toolset() -> McpToolset:
    """ADK toolset wrapping the official Fivetran MCP server (stdio)."""
    return McpToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(
                command=settings.fivetran_mcp_command,
                args=settings.fivetran_mcp_argv,
                env={
                    "FIVETRAN_API_KEY": settings.fivetran_api_key,
                    "FIVETRAN_API_SECRET": settings.fivetran_api_secret,
                    "FIVETRAN_ALLOW_WRITES": (
                        "true" if settings.fivetran_allow_writes else "false"
                    ),
                },
            ),
            timeout=settings.fivetran_mcp_timeout,
        ),
        tool_filter=[
            "list_connections",
            "list_metadata_connectors",
            "create_connection",
            "sync_connection",
            "modify_connection_schema_config",
        ],
        tool_name_prefix="fivetran",
    )
