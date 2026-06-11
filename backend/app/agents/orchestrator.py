"""Multi-step OpenAid provisioning orchestrator.

Plans humanitarian data missions, pauses for human approval before Fivetran
writes, then provisions connectors and generates briefings.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Any

from app.config import settings
from app.models import AgentStep, ApprovalRequest, StepStatus
from app.tools.bigquery_briefing import demo_briefing
from app.tools.fivetran_gateway import FivetranGateway
from app.tools.gemini_reason import interpret_mission, plan_connector_strategy
from app.tools.hdx_search import pick_best_dataset, search_hdx_datasets


class MissionSession:
    def __init__(self, prompt: str) -> None:
        self.id = str(uuid.uuid4())
        self.prompt = prompt
        self.steps: list[AgentStep] = []
        self.approval: ApprovalRequest | None = None
        self.approval_event = asyncio.Event()
        self.approval_decision: bool | None = None
        self.briefing: str | None = None
        self.interpretation: dict[str, Any] | None = None
        self._queue: asyncio.Queue[AgentStep | ApprovalRequest | str] = asyncio.Queue()

    async def emit(self, item: AgentStep | ApprovalRequest | str) -> None:
        await self._queue.put(item)

    async def events(self) -> AsyncIterator[AgentStep | ApprovalRequest | str]:
        while True:
            item = await self._queue.get()
            yield item
            if isinstance(item, str) and item == "__DONE__":
                break

    def _upsert_step(self, step: AgentStep) -> None:
        for i, existing in enumerate(self.steps):
            if existing.id == step.id:
                self.steps[i] = step
                return
        self.steps.append(step)

    async def _run_step(self, step_id: str, label: str, tool: str, coro) -> Any:
        step = AgentStep(id=step_id, label=label, status=StepStatus.RUNNING, tool=tool)
        self._upsert_step(step)
        await self.emit(step)
        try:
            result = await coro
            step.status = StepStatus.COMPLETED
            step.detail = str(result)[:300] if result is not None else "done"
            step.payload = result if isinstance(result, dict) else {"result": result}
            self._upsert_step(step)
            await self.emit(step)
            return result
        except Exception as exc:  # noqa: BLE001
            step.status = StepStatus.FAILED
            step.detail = str(exc)
            self._upsert_step(step)
            await self.emit(step)
            raise

    async def run(self) -> None:
        fivetran = FivetranGateway()

        # Step 1 — interpret mission (Gemini via ADK)
        interpretation = await self._run_step(
            "interpret",
            "Interpreting humanitarian data request",
            "gemini.reason",
            interpret_mission(self.prompt),
        )
        self.interpretation = (
            interpretation.model_dump()
            if hasattr(interpretation, "model_dump")
            else interpretation
        )
        region = (self.interpretation or {}).get("region") or "target region"
        hdx_query = (self.interpretation or {}).get("hdx_query") or (
            f"{region} flood health medical supplies"
        )

        # Step 2 — hunt datasets on HDX
        datasets = await self._run_step(
            "hdx_search",
            f"Searching HDX: {hdx_query[:80]}",
            "hdx.search",
            search_hdx_datasets(hdx_query),
        )

        best = pick_best_dataset(datasets if isinstance(datasets, list) else [])
        if not best:
            await self.emit("__DONE__")
            return

        # Step 3 — gap analysis against existing Fivetran connections (MCP → REST)
        connections = []
        try:
            connections = await self._run_step(
                "gap_analysis",
                "Analyzing existing Fivetran connections for coverage gaps",
                "fivetran.mcp.list_connections",
                self._list_connections(fivetran),
            )
        except Exception:
            connections = []

        has_coverage = any(
            best.get("name", "").lower() in (c.get("schema", "") or "").lower()
            for c in (connections or [])
        )

        # Step 4 — choose connector strategy
        connector_plan = await self._run_step(
            "connector_strategy",
            "Selecting connector strategy from Fivetran metadata",
            "fivetran.mcp.list_metadata_connectors",
            self._build_connector_plan(best, has_coverage, fivetran),
        )

        # Step 5 — approval gate (required before writes)
        self.approval = ApprovalRequest(
            session_id=self.id,
            step_id="provision",
            title="Approve pipeline provisioning plan",
            summary=(
                f"Provision a new pipeline for **{best.get('title')}** "
                f"targeting **{region}**. Connector: {connector_plan.get('service')}."
            ),
            plan=connector_plan,
        )
        await self.emit(self.approval)

        provision_step = AgentStep(
            id="provision",
            label="Awaiting operator approval to provision pipeline",
            status=StepStatus.WAITING_APPROVAL,
            tool="human.approval",
        )
        self._upsert_step(provision_step)
        await self.emit(provision_step)

        await self.approval_event.wait()
        if not self.approval_decision:
            provision_step.status = StepStatus.SKIPPED
            provision_step.detail = "Operator rejected the provisioning plan."
            self._upsert_step(provision_step)
            await self.emit(provision_step)
            await self.emit("__DONE__")
            return

        # Step 6 — provision (demo-safe)
        if settings.demo_mode or not settings.fivetran_allow_writes:
            await self._run_step(
                "provision",
                "Provisioning connector (demo simulation)",
                "fivetran.create_connection",
                self._simulate_provision(connector_plan),
            )
        else:
            await self._run_step(
                "provision",
                "Creating Fivetran connection (paused)",
                "fivetran.mcp.create_connection",
                fivetran.create_connection(connector_plan["create_body"]),
            )

        # Step 7 — schema policy
        await self._run_step(
            "schema_policy",
            "Applying schema change policy (ALLOW_COLUMNS)",
            "fivetran.modify_connection_schema_config",
            {"schema_change_handling": "ALLOW_COLUMNS", "enabled_tables": connector_plan.get("tables", [])},
        )

        # Step 8 — briefing
        self.briefing = demo_briefing(best.get("title", "HDX Dataset"), region)
        briefing_step = AgentStep(
            id="briefing",
            label="Generating field briefing",
            status=StepStatus.COMPLETED,
            tool="bigquery.briefing",
            detail="Briefing ready",
            payload={"briefing": self.briefing},
        )
        self._upsert_step(briefing_step)
        await self.emit(briefing_step)
        await self.emit("__DONE__")

    async def _list_connections(self, fivetran: FivetranGateway) -> dict:
        items = await fivetran.list_connections()
        return {
            "backend": fivetran.last_backend,
            "tool": fivetran.last_tool,
            "count": len(items),
            "items": items[:10],
        }

    async def _build_connector_plan(
        self, dataset: dict, has_coverage: bool, fivetran: FivetranGateway
    ) -> dict:
        metadata: list[dict] = []
        try:
            metadata = await fivetran.list_metadata_connectors()
        except Exception:
            pass
        mcp_backend = fivetran.last_backend

        strategy = await plan_connector_strategy(dataset, has_coverage, metadata)
        service = strategy.service
        tables = strategy.tables or ["humanitarian_records"]

        # Ensure connector_sdk if metadata lists it and Gemini picked an unknown id
        known_ids = {m.get("id") for m in metadata}
        if known_ids and service not in known_ids and "connector_sdk" in known_ids:
            service = "connector_sdk"

        resource = (dataset.get("resources") or [{}])[0]
        return {
            "fivetran_backend": mcp_backend,
            "fivetran_tool": fivetran.last_tool,
            "service": service,
            "rationale": strategy.rationale,
            "dataset": dataset.get("title"),
            "resource_url": resource.get("url"),
            "resource_format": resource.get("format"),
            "gap_detected": not has_coverage,
            "tables": tables,
            "create_body": {
                "service": service,
                "group_id": settings.fivetran_group_id,
                "paused": True,
                "sync_frequency": 360,
                "config": {
                    "schema": dataset.get("name", "openaid_dataset")[:63],
                    "table": tables[0] if tables else "humanitarian_records",
                    "source_url": resource.get("url"),
                },
            },
        }

    async def _simulate_provision(self, plan: dict) -> dict:
        await asyncio.sleep(0.5)
        return {
            "connection_id": "demo_connection_openaid",
            "status": "paused",
            "plan": plan,
            "note": "Demo mode — set FIVETRAN_ALLOW_WRITES=true for live provisioning",
        }


# In-memory session store (swap for Redis in production)
SESSIONS: dict[str, MissionSession] = {}


def create_session(prompt: str) -> MissionSession:
    session = MissionSession(prompt)
    SESSIONS[session.id] = session
    return session


def get_session(session_id: str) -> MissionSession | None:
    return SESSIONS.get(session_id)
