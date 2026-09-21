from __future__ import annotations

from app.agent.llm import complete_json
from app.demo import BUGGY_CODE, FIXED_CODE
from app.models import (
    Finding,
    InvestigationPlan,
    InvestigationReport,
    ProposedFix,
    ToolResult,
)


def analyze(ticket: str, plan: InvestigationPlan, evidence: list[ToolResult]) -> InvestigationReport:
    payload = complete_json(
        system=(
            "You are a staff engineer writing a support investigation report. "
            "Return JSON with keys: issue_summary, root_cause, findings "
            "(list of {source, title, detail, references}), proposed_fix "
            "({summary, file_path, current_code, suggested_code, "
            "configuration_changes, verification_steps}), references. "
            "Ground every claim in the provided evidence. Include a concrete code fix "
            "when GitHub diffs or stack traces identify a file."
        ),
        user=(
            f"Ticket: {ticket}\nPlan: {plan.model_dump_json()}\n"
            f"Evidence: {[item.model_dump() for item in evidence]}"
        ),
    )
    if payload:
        try:
            return InvestigationReport(
                issue_summary=str(payload.get("issue_summary") or ticket),
                extracted=plan.extracted,
                plan=[step.goal for step in plan.steps],
                findings=[Finding.model_validate(item) for item in payload.get("findings") or []],
                root_cause=str(payload.get("root_cause") or "See findings."),
                proposed_fix=ProposedFix.model_validate(payload.get("proposed_fix") or {"summary": ""}),
                references=list(payload.get("references") or []),
            )
        except Exception:
            pass
    return _deterministic_report(ticket, plan, evidence)


def _deterministic_report(
    ticket: str, plan: InvestigationPlan, evidence: list[ToolResult]
) -> InvestigationReport:
    findings = _findings_from_evidence(evidence)
    references = []
    for item in evidence:
        references.extend(item.references)
    signature, stack, path = _first_stack(evidence)
    commit = _best_commit(evidence)
    user = _affected_user(evidence)
    login_issue = (plan.extracted.feature == "login") or (
        signature and "expires_at" in signature
    )

    if login_issue and commit:
        root_cause = (
            f"Login started returning HTTP 500 after commit {commit.get('sha')} "
            f"(\"{commit.get('message')}\") deployed to auth-service. "
            "`validate_session` now reads token['expires_at'] without a fallback, "
            "which raises KeyError for legacy refresh sessions that omit expiry. "
            + (_user_clause(user))
        )
        proposed = ProposedFix(
            summary=(
                "Guard missing `expires_at` in `validate_session` so legacy refresh "
                "sessions remain valid until revoked, instead of crashing login with a 500."
            ),
            file_path="app/auth/session.py",
            current_code=commit.get("diff") or BUGGY_CODE,
            suggested_code=FIXED_CODE,
            configuration_changes=[
                "No config change required. Optional: emit a metric when a legacy token without expires_at is accepted, so the compatibility path can be removed later."
            ],
            verification_steps=[
                "Add a unit test: validate_session({'revoked': False}) is True.",
                "Add a unit test: validate_session({'expires_at': past ISO timestamp}) is False.",
                "Replay login for a legacy_refresh user (jane.doe@acme.com) and confirm HTTP 200.",
                "Confirm auth-service /api/auth/login 5m error rate returns to baseline.",
            ],
        )
        issue_summary = (
            "Users cannot log in: POST /api/auth/login returns HTTP 500 with "
            "KeyError: 'expires_at' starting at the 2.14.1 auth-service deploy."
        )
    else:
        root_cause = (
            "The combined logs, API status, and GitHub history did not identify a "
            "single high-confidence code fault. The proposed next step is to keep "
            "the failing request path instrumented and review the most recent related commits."
        )
        if signature:
            root_cause = (
                f"Errors matching `{signature}` were found"
                + (f" on {path}" if path else "")
                + ". Review the latest related GitHub changes and add handling for this exception at the boundary."
            )
        proposed = ProposedFix(
            summary="Capture the failing exception at the API boundary and return a controlled 4xx/401 instead of a 500, then inspect the most relevant recent commit.",
            file_path=path,
            current_code=stack,
            suggested_code=None,
            configuration_changes=[],
            verification_steps=[
                "Reproduce using the request IDs from application logs.",
                "Confirm service status and error rate after a guarded deploy.",
            ],
        )
        issue_summary = plan.understanding

    return InvestigationReport(
        issue_summary=issue_summary,
        extracted=plan.extracted,
        plan=[f"{step.order}. {step.goal}" for step in plan.steps],
        findings=findings,
        root_cause=root_cause.strip(),
        proposed_fix=proposed,
        references=list(dict.fromkeys(references)),
    )


def _findings_from_evidence(evidence: list[ToolResult]) -> list[Finding]:
    findings: list[Finding] = []
    for item in evidence:
        findings.append(
            Finding(
                source=item.tool,
                title=f"{item.tool}:{item.action}",
                detail=item.summary,
                references=item.references,
            )
        )
    return findings


def _first_stack(evidence: list[ToolResult]) -> tuple[str | None, str | None, str | None]:
    for item in evidence:
        data = item.data or {}
        rows = data.get("rows") or data.get("recent_logs") or []
        for row in rows:
            if row.get("stack_trace") or row.get("error_signature"):
                return row.get("error_signature"), row.get("stack_trace"), row.get("path")
    return None, None, None


def _best_commit(evidence: list[ToolResult]) -> dict | None:
    for item in evidence:
        if item.tool != "github":
            continue
        data = item.data or {}
        nested_diff = data.get("diff")
        if isinstance(nested_diff, dict) and nested_diff.get("sha"):
            return nested_diff
        if item.action == "get_commit_diff" and isinstance(data, dict) and data.get("sha"):
            return data
        commits = data.get("commits")
        if isinstance(commits, dict):
            commits = commits.get("commits") or []
        if isinstance(commits, list) and commits:
            return commits[0]
    return None


def _user_clause(user: dict | None) -> str:
    if not user or not user.get("email"):
        return ""
    session_type = user.get("session_type")
    if session_type:
        return (
            f"Affected example user {user['email']} has session_type={session_type}."
        )
    return f"Affected example user {user['email']}."


def _as_profile(value: object) -> dict | None:
    if not isinstance(value, dict):
        return None
    if value.get("email") and (value.get("session_type") or value.get("name") or value.get("id")):
        return value
    nested = value.get("user")
    if isinstance(nested, dict) and nested.get("email"):
        return nested
    return None


def _affected_user(evidence: list[ToolResult]) -> dict | None:
    profiles: list[dict] = []
    log_emails: list[str] = []
    for item in evidence:
        data = item.data or {}
        profile = _as_profile(data.get("user"))
        if profile:
            profiles.append(profile)
        for row in data.get("rows") or data.get("recent_logs") or []:
            email = row.get("user_email")
            if email:
                log_emails.append(email)
    if profiles:
        typed = [item for item in profiles if item.get("session_type")]
        return typed[0] if typed else profiles[0]
    if log_emails:
        return {"email": log_emails[0]}
    return None
