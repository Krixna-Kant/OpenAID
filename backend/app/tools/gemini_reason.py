"""Gemini reasoning via Google ADK — mission interpretation and connector strategy."""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


class MissionInterpretation(BaseModel):
    """Structured output from Gemini mission interpretation."""

    intent: str = Field(description="e.g. provision_new_pipeline, refresh_existing")
    urgency: str = Field(description="low | medium | high")
    domain: str = Field(description="e.g. humanitarian_health, logistics")
    region: str | None = Field(default=None, description="Target geography if mentioned")
    hdx_query: str = Field(description="Search query for HDX CKAN API")
    summary: str = Field(description="One-line operator summary")


class ConnectorStrategy(BaseModel):
    """Structured connector plan from Gemini."""

    service: str
    rationale: str
    tables: list[str] = Field(default_factory=list)


def is_gemini_configured() -> bool:
    return settings.gemini_configured


def _fallback_interpret(prompt: str) -> MissionInterpretation:
    """Regex fallback when Gemini is unavailable or errors."""
    region_match = re.search(
        r"\b(Kenya|Uganda|Somalia|Sudan|Haiti|Malawi|Ethiopia|Nigeria|Yemen)\b",
        prompt,
        re.I,
    )
    region = region_match.group(1) if region_match else None
    hdx_query = f"{region or 'humanitarian'} flood health medical supplies"
    return MissionInterpretation(
        intent="provision_new_pipeline",
        urgency="high",
        domain="humanitarian_health",
        region=region,
        hdx_query=hdx_query,
        summary=prompt[:200],
    )


def _fallback_connector_strategy(has_coverage: bool) -> ConnectorStrategy:
    return ConnectorStrategy(
        service="connector_sdk",
        rationale=(
            "HDX humanitarian sources are typically custom CSV/JSON URLs; "
            "Connector SDK is the standard approach for ad-hoc crisis datasets."
        ),
        tables=["humanitarian_records"],
    )


async def interpret_mission(prompt: str) -> MissionInterpretation:
    """Interpret operator prompt with Gemini (ADK), falling back to heuristics."""
    if not is_gemini_configured():
        return _fallback_interpret(prompt)

    try:
        from app.agents.adk_agent import interpret_mission_with_adk

        return await interpret_mission_with_adk(prompt)
    except Exception as exc:
        logger.warning("Gemini mission interpretation failed, using fallback: %s", exc)
        return _fallback_interpret(prompt)


async def plan_connector_strategy(
    dataset: dict[str, Any],
    has_coverage: bool,
    metadata_connectors: list[dict[str, Any]] | None = None,
) -> ConnectorStrategy:
    """Choose connector strategy with Gemini (ADK), falling back to connector_sdk."""
    if not is_gemini_configured():
        return _fallback_connector_strategy(has_coverage)

    try:
        from app.agents.adk_agent import plan_connector_with_adk

        return await plan_connector_with_adk(dataset, has_coverage, metadata_connectors)
    except Exception as exc:
        logger.warning("Gemini connector strategy failed, using fallback: %s", exc)
        return _fallback_connector_strategy(has_coverage)
