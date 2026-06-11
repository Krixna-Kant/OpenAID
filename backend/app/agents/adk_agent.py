"""Google ADK agents for OpenAid reasoning steps."""

from __future__ import annotations

import json
import uuid
from typing import TypeVar

from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.utils._schema_utils import validate_schema
from google.genai import types
from pydantic import BaseModel

from app.config import settings
from app.gcp_runtime import configure_gcp_runtime
from app.tools.gemini_reason import ConnectorStrategy, MissionInterpretation

T = TypeVar("T", bound=BaseModel)

APP_NAME = "openaid_provisioner"


def _ensure_google_credentials() -> None:
    """Configure Vertex AI (GCP) or AI Studio API key before ADK runs."""
    configure_gcp_runtime()


def get_planned_model() -> str:
    return settings.gemini_model


def is_adk_ready() -> bool:
    return settings.gemini_configured


def _mission_interpreter_agent() -> LlmAgent:
    return LlmAgent(
        name="mission_interpreter",
        model=settings.gemini_model,
        description="Interprets humanitarian data requests for pipeline provisioning.",
        instruction=(
            "You are OpenAid Provisioner, an AI agent helping NGO operators "
            "provision humanitarian data pipelines.\n\n"
            "Given an operator message, extract:\n"
            "- intent: provision_new_pipeline | refresh_existing | explore_only\n"
            "- urgency: low | medium | high\n"
            "- domain: e.g. humanitarian_health, logistics, shelter, nutrition\n"
            "- region: country or region name if mentioned, else null\n"
            "- hdx_query: a concise CKAN search query for HDX (Humanitarian Data Exchange) "
            "including geography, crisis type, and data topic\n"
            "- summary: one sentence for the operator dashboard"
        ),
        output_schema=MissionInterpretation,
        include_contents="none",
    )


def _connector_strategist_agent() -> LlmAgent:
    return LlmAgent(
        name="connector_strategist",
        model=settings.gemini_model,
        description="Selects Fivetran connector strategy for an HDX dataset.",
        instruction=(
            "You are a data engineering agent choosing a Fivetran connector strategy.\n\n"
            "For humanitarian HDX datasets (CSV/JSON URLs), prefer service=connector_sdk "
            "unless metadata shows a better native connector.\n\n"
            "Return service (connector id), rationale (2-3 sentences), and tables "
            "(list of table names to enable, default humanitarian_records)."
        ),
        output_schema=ConnectorStrategy,
        include_contents="none",
    )


async def run_structured_agent(agent: LlmAgent, user_prompt: str) -> BaseModel:
    """Run a single-turn ADK agent and return validated structured output."""
    _ensure_google_credentials()

    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )

    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id="openaid_operator",
        session_id=str(uuid.uuid4()),
    )

    message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_prompt)],
    )

    last_text = ""
    try:
        async for event in runner.run_async(
            user_id=session.user_id,
            session_id=session.id,
            new_message=message,
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text and not part.thought:
                        last_text = part.text
    finally:
        await runner.close()

    if not last_text:
        raise RuntimeError(f"ADK agent {agent.name} returned no content")

    if agent.output_schema is None:
        raise RuntimeError(f"ADK agent {agent.name} has no output_schema")

    result = validate_schema(agent.output_schema, last_text)
    if isinstance(result, BaseModel):
        return result
    if isinstance(result, dict):
        return agent.output_schema.model_validate(result)
    return agent.output_schema.model_validate(json.loads(str(result)))


async def interpret_mission_with_adk(prompt: str) -> MissionInterpretation:
    agent = _mission_interpreter_agent()
    result = await run_structured_agent(agent, prompt)
    if not isinstance(result, MissionInterpretation):
        return MissionInterpretation.model_validate(result.model_dump())
    return result


async def plan_connector_with_adk(
    dataset: dict,
    has_coverage: bool,
    metadata_connectors: list[dict] | None,
) -> ConnectorStrategy:
    connector_ids = [c.get("id") for c in (metadata_connectors or []) if c.get("id")]
    user_prompt = json.dumps(
        {
            "dataset_title": dataset.get("title"),
            "dataset_name": dataset.get("name"),
            "resource_formats": [
                r.get("format") for r in dataset.get("resources", []) if r.get("format")
            ],
            "has_existing_fivetran_coverage": has_coverage,
            "available_connectors_sample": connector_ids[:25],
        },
        indent=2,
    )
    agent = _connector_strategist_agent()
    result = await run_structured_agent(agent, user_prompt)
    if not isinstance(result, ConnectorStrategy):
        return ConnectorStrategy.model_validate(result.model_dump())
    return result
