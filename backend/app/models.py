from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentStep(BaseModel):
    id: str
    label: str
    status: StepStatus = StepStatus.PENDING
    detail: str | None = None
    tool: str | None = None
    payload: dict[str, Any] | None = None


class ApprovalRequest(BaseModel):
    session_id: str
    step_id: str
    title: str
    summary: str
    plan: dict[str, Any]


class MissionRequest(BaseModel):
    prompt: str = Field(
        ...,
        min_length=10,
        examples=[
            "We need the latest medical supply data for flooded regions in Kenya, but our dashboard is empty."
        ],
    )


class MissionResponse(BaseModel):
    session_id: str
    briefing: str | None = None
    steps: list[AgentStep] = Field(default_factory=list)


class ApprovalDecision(BaseModel):
    approved: bool
    comment: str | None = None
