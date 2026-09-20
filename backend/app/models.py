from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class TicketRequest(BaseModel):
    ticket: str = Field(min_length=8, max_length=4000)
    reporter_email: str | None = None


class ExtractedDetails(BaseModel):
    symptom: str
    error_code: str | None = None
    feature: str | None = None
    timeframe: str | None = None
    user_hint: str | None = None
    keywords: list[str] = Field(default_factory=list)


class PlanStep(BaseModel):
    order: int
    tool: Literal["database", "api", "github", "analyze"]
    goal: str


class InvestigationPlan(BaseModel):
    understanding: str
    extracted: ExtractedDetails
    steps: list[PlanStep]


class ToolResult(BaseModel):
    tool: str
    action: str
    summary: str
    data: Any = None
    references: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    source: str
    title: str
    detail: str
    references: list[str] = Field(default_factory=list)


class ProposedFix(BaseModel):
    summary: str
    file_path: str | None = None
    current_code: str | None = None
    suggested_code: str | None = None
    configuration_changes: list[str] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)


class InvestigationReport(BaseModel):
    issue_summary: str
    extracted: ExtractedDetails
    plan: list[str]
    findings: list[Finding]
    root_cause: str
    proposed_fix: ProposedFix
    references: list[str]


class AgentEvent(BaseModel):
    type: str
    stage: str
    title: str
    detail: Any = None
    done: bool = False
