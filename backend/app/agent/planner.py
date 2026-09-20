from __future__ import annotations

import re

from app.agent.llm import complete_json
from app.models import ExtractedDetails, InvestigationPlan, PlanStep, ToolResult

FEATURE_HINTS = {
    "login": ["login", "sign in", "signin", "auth", "password", "session"],
    "checkout": ["checkout", "payment", "cart", "billing"],
    "search": ["search", "results"],
    "notifications": ["email", "notification", "push"],
}


def _extract_email(text: str) -> str | None:
    match = re.search(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.I)
    return match.group(0) if match else None


def _extract_status(text: str) -> str | None:
    match = re.search(r"\b([45]\d\d)\b", text)
    return match.group(1) if match else None


def _extract_feature(text: str) -> str | None:
    lowered = text.lower()
    for feature, hints in FEATURE_HINTS.items():
        if any(hint in lowered for hint in hints):
            return feature
    return None


def _timeframe(text: str) -> str | None:
    lowered = text.lower()
    for phrase in ("since yesterday", "yesterday", "today", "last week", "last night"):
        if phrase in lowered:
            return phrase
    return None


def _keywords(ticket: str, extracted: ExtractedDetails) -> list[str]:
    words = []
    if extracted.feature:
        words.append(extracted.feature)
    if extracted.error_code:
        words.append(extracted.error_code)
    for extra in ("login", "auth", "session", "error"):
        if extra in ticket.lower() and extra not in words:
            words.append(extra)
    return words[:6]


def extract_details(ticket: str, reporter_email: str | None = None) -> ExtractedDetails:
    feature = _extract_feature(ticket)
    error_code = _extract_status(ticket)
    extracted = ExtractedDetails(
        symptom=ticket.strip().split("\n")[0][:240],
        error_code=error_code,
        feature=feature,
        timeframe=_timeframe(ticket),
        user_hint=_extract_email(ticket) or reporter_email,
        keywords=[],
    )
    extracted.keywords = _keywords(ticket, extracted)
    return extracted


def build_plan(ticket: str, reporter_email: str | None = None) -> InvestigationPlan:
    llm_plan = complete_json(
        system=(
            "You plan investigations for a support-ticket agent. "
            "Return JSON with keys: understanding, extracted "
            "(symptom, error_code, feature, timeframe, user_hint, keywords), "
            "and steps (list of {order, tool, goal}) where tool is one of "
            "database, api, github, analyze. Use database then api then github "
            "before analyze unless the ticket clearly needs a different order."
        ),
        user=json_user(ticket, reporter_email),
    )
    if llm_plan:
        try:
            extracted = ExtractedDetails.model_validate(llm_plan.get("extracted") or {})
            steps = [PlanStep.model_validate(step) for step in llm_plan.get("steps") or []]
            if extracted.symptom and steps:
                return InvestigationPlan(
                    understanding=str(llm_plan.get("understanding") or extracted.symptom),
                    extracted=extracted,
                    steps=steps,
                )
        except Exception:
            pass

    extracted = extract_details(ticket, reporter_email)
    feature = extracted.feature or "the reported"
    hours = "since yesterday" if extracted.timeframe else "in the recent window"
    return InvestigationPlan(
        understanding=(
            f"The ticket describes a {feature} issue"
            + (f" returning HTTP {extracted.error_code}" if extracted.error_code else "")
            + f" {hours}. Investigate application logs, service APIs, and recent GitHub changes."
        ),
        extracted=extracted,
        steps=[
            PlanStep(
                order=1,
                tool="database",
                goal="Search application logs and user records for matching errors.",
            ),
            PlanStep(
                order=2,
                tool="api",
                goal="Call service-status and domain APIs for health and extra context.",
            ),
            PlanStep(
                order=3,
                tool="github",
                goal="Search recent commits and pull requests related to the failing area.",
            ),
            PlanStep(
                order=4,
                tool="analyze",
                goal="Combine evidence, identify the root cause, and propose a fix.",
            ),
        ],
    )


def json_user(ticket: str, reporter_email: str | None) -> str:
    return (
        f"Support ticket:\n{ticket}\n\n"
        f"Reporter email: {reporter_email or 'unknown'}"
    )


def decide_next_action(
    plan: InvestigationPlan,
    evidence: list[ToolResult],
    iterations: int,
    max_iterations: int,
) -> tuple[str, str]:
    """Return (tool_name, goal). tool_name may be 'analyze'."""
    used = {item.tool for item in evidence}
    llm_decision = complete_json(
        system=(
            "Decide the next investigation action. Return JSON "
            "{tool: database|api|github|analyze, goal: string, reason: string}. "
            "Call analyze when logs, API status, and GitHub changes are present "
            "or when more tools will not help. Never invent tool names."
        ),
        user=(
            f"Plan: {plan.model_dump_json()}\n"
            f"Evidence so far: {[item.model_dump() for item in evidence]}\n"
            f"Iterations: {iterations}/{max_iterations}"
        ),
    )
    if llm_decision and llm_decision.get("tool") in {"database", "api", "github", "analyze"}:
        if iterations >= max_iterations:
            return "analyze", "Iteration budget reached; analyze current evidence."
        return str(llm_decision["tool"]), str(llm_decision.get("goal") or "Continue investigation.")

    for step in plan.steps:
        if step.tool == "analyze":
            continue
        if step.tool not in used:
            return step.tool, step.goal

    needs_user = bool(plan.extracted.user_hint) and not any(
        item.action == "get_user" for item in evidence
    )
    if needs_user and "database" in used and iterations < max_iterations:
        return "database", f"Look up user {plan.extracted.user_hint} now that logs confirmed the issue."

    signature = _error_signature(evidence)
    if (
        signature
        and not any(item.action == "related_errors" for item in evidence)
        and iterations < max_iterations
    ):
        return "database", f"Group related errors for signature {signature}."

    return "analyze", "Enough evidence collected; produce the root cause and proposed fix."


def _error_signature(evidence: list[ToolResult]) -> str | None:
    for item in evidence:
        if item.tool != "database":
            continue
        rows = (item.data or {}).get("rows") or []
        for row in rows:
            if row.get("error_signature"):
                return row["error_signature"]
    return None
