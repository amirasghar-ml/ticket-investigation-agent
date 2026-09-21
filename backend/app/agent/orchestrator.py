from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from app.agent.analyzer import analyze
from app.agent.planner import build_plan, decide_next_action
from app.config import settings
from app.models import AgentEvent, InvestigationPlan, TicketRequest, ToolResult
from app.tools import ApiTool, DatabaseTool, GitHubTool


def _event(event_type: str, stage: str, title: str, detail=None, done: bool = False) -> AgentEvent:
    return AgentEvent(type=event_type, stage=stage, title=title, detail=detail, done=done)


class SupportTicketAgent:
    """Orchestrator: plan, call tools, iterate, then propose a fix."""

    def __init__(self) -> None:
        self.database = DatabaseTool()
        self.api = ApiTool()
        self.github = GitHubTool()

    async def investigate(self, request: TicketRequest) -> AsyncIterator[AgentEvent]:
        ticket = request.ticket.strip()
        yield _event(
            "ticket_received",
            "receive",
            "Agent received the support ticket",
            {"ticket": ticket, "reporter_email": request.reporter_email},
        )

        plan = build_plan(ticket, request.reporter_email)
        yield _event(
            "plan_created",
            "plan",
            "Investigation plan ready",
            {
                "understanding": plan.understanding,
                "extracted": plan.extracted.model_dump(),
                "steps": [step.model_dump() for step in plan.steps],
            },
        )

        evidence: list[ToolResult] = []
        for iteration in range(1, settings.max_tool_iterations + 1):
            tool_name, goal = decide_next_action(
                plan, evidence, iteration, settings.max_tool_iterations
            )
            if tool_name == "analyze":
                yield _event(
                    "reasoning",
                    "orchestrator",
                    "Enough evidence collected — moving to root-cause analysis",
                    {"goal": goal, "iteration": iteration},
                )
                break

            yield _event(
                "tool_started",
                "orchestrator",
                f"Calling {tool_name} tool",
                {"tool": tool_name, "goal": goal, "iteration": iteration},
            )
            result = await asyncio.to_thread(self._run_tool, tool_name, goal, plan, evidence)
            evidence.append(result)
            yield _event(
                "tool_completed",
                "orchestrator",
                result.summary,
                {
                    "tool": result.tool,
                    "action": result.action,
                    "summary": result.summary,
                    "data": result.data,
                    "references": result.references,
                    "iteration": iteration,
                },
            )
            if iteration < settings.max_tool_iterations:
                yield _event(
                    "iterating",
                    "orchestrator",
                    "Checking whether more information is needed",
                    {"iteration": iteration, "tools_used": [item.tool for item in evidence]},
                )
            await asyncio.sleep(0.15)

        yield _event(
            "analysis_started",
            "analyze",
            "Analyzing findings and drafting a proposed fix",
            {"evidence_count": len(evidence)},
        )
        report = analyze(ticket, plan, evidence)
        yield _event(
            "report_ready",
            "output",
            "Investigation complete",
            report.model_dump(),
            done=True,
        )

    def _run_tool(
        self,
        tool_name: str,
        goal: str,
        plan: InvestigationPlan,
        evidence: list[ToolResult],
    ) -> ToolResult:
        extracted = plan.extracted
        if tool_name == "database":
            goal_l = goal.lower()
            looking_up_user = bool(extracted.user_hint) and any(
                phrase in goal_l for phrase in ("look up user", "get user", "user profile")
            )
            if looking_up_user:
                return self.database.get_user(extracted.user_hint)
            if "signature" in goal_l or "related error" in goal_l:
                signature = extracted.feature or "error"
                for item in evidence:
                    for row in _log_rows(item):
                        if row.get("error_signature"):
                            signature = row["error_signature"]
                            break
                return self.database.related_errors(signature)
            status_code = int(extracted.error_code) if extracted.error_code else 500
            path = "/api/auth/login" if extracted.feature == "login" else None
            keywords = extracted.keywords or ([extracted.feature] if extracted.feature else None)
            hours = 48 if extracted.timeframe else 72
            return self.database.search_logs(
                keywords=keywords,
                status_code=status_code if extracted.error_code else None,
                hours=hours,
                path=path,
            )

        if tool_name == "api":
            status = self.api.service_status()
            metrics = self.api.auth_metrics() if extracted.feature in {None, "login", "auth"} else None
            user = self.api.fetch_user(extracted.user_hint) if extracted.user_hint else None
            combined = {
                "services": status.data,
                "metrics": None if metrics is None else metrics.data,
                "user": None if user is None else user.data,
            }
            summary = status.summary
            if metrics:
                summary += " " + metrics.summary
            refs = list(status.references)
            if metrics:
                refs.extend(metrics.references)
            return ToolResult(
                tool="api",
                action="service_status+metrics",
                summary=summary.strip(),
                data=combined,
                references=refs,
            )

        if tool_name == "github":
            query = " ".join(
                part
                for part in [extracted.feature, "session", "login", "auth", extracted.error_code]
                if part
            )
            changes = self.github.search_code_changes(query)
            pulls = self.github.search_pull_requests(query)
            sha = None
            commits = (changes.data or {}).get("commits") or []
            if commits:
                sha = commits[0].get("sha")
            diff = self.github.get_commit_diff(sha) if sha else None
            data = {
                "commits": commits,
                "pull_requests": (pulls.data or {}).get("pull_requests"),
                "diff": None if diff is None else diff.data,
            }
            summary = f"{changes.summary} {pulls.summary}"
            refs = changes.references + pulls.references
            if diff:
                summary += " " + diff.summary
                refs.extend(diff.references)
            return ToolResult(
                tool="github",
                action="search_changes+prs+diff",
                summary=summary.strip(),
                data=data,
                references=list(dict.fromkeys(refs)),
            )

        return ToolResult(
            tool=tool_name,
            action="unknown",
            summary=f"Unknown tool '{tool_name}' was requested.",
            data={"goal": goal},
        )


def _log_rows(item: ToolResult) -> list:
    data = item.data or {}
    return data.get("rows") or data.get("recent_logs") or []


async def run_investigation(request: TicketRequest) -> AsyncIterator[AgentEvent]:
    agent = SupportTicketAgent()
    async for event in agent.investigate(request):
        yield event
