from __future__ import annotations

from typing import Any

import httpx

from app.demo import ERROR_METRICS, SERVICE_STATUS, USERS
from app.models import ToolResult


class ApiTool:
    """Calls internal service APIs. Demo mode returns seeded microservice data."""

    name = "api"

    def __init__(self, live_base_url: str | None = None) -> None:
        self.live_base_url = live_base_url

    def service_status(self) -> ToolResult:
        if self.live_base_url:
            return self._live_get("/internal/services/status", "service_status")
        degraded = [s for s in SERVICE_STATUS if s["status"] != "healthy"]
        names = ", ".join(s["name"] for s in degraded) or "none"
        return ToolResult(
            tool=self.name,
            action="service_status",
            summary=f"Checked service status. Degraded: {names}.",
            data={"services": SERVICE_STATUS},
            references=[f"api:status:{s['name']}" for s in SERVICE_STATUS],
        )

    def auth_metrics(self) -> ToolResult:
        if self.live_base_url:
            return self._live_get("/internal/auth/metrics", "auth_metrics")
        rate = ERROR_METRICS["error_rate"]
        return ToolResult(
            tool=self.name,
            action="auth_metrics",
            summary=(
                f"Auth login error rate is {rate:.0%} "
                f"({ERROR_METRICS['error_count']}/{ERROR_METRICS['total_requests']} "
                f"in {ERROR_METRICS['window']}). Top error: {ERROR_METRICS['top_error']}."
            ),
            data=ERROR_METRICS,
            references=["api:auth-service:/api/auth/login"],
        )

    def fetch_user(self, email: str) -> ToolResult:
        if self.live_base_url:
            return self._live_get(f"/internal/users/{email}", "fetch_user")
        user = next((u for u in USERS if u["email"].lower() == email.lower()), None)
        if not user:
            return ToolResult(
                tool=self.name,
                action="fetch_user",
                summary=f"User profile API returned 404 for {email}.",
                data={"email": email, "user": None},
            )
        return ToolResult(
            tool=self.name,
            action="fetch_user",
            summary=(
                f"Profile API: {user['name']} is {user['status']} "
                f"with session_type={user['session_type']}."
            ),
            data={"user": user},
            references=[f"api:users/{user['id']}"],
        )

    def _live_get(self, path: str, action: str) -> ToolResult:
        url = f"{self.live_base_url.rstrip('/')}{path}"
        try:
            response = httpx.get(url, timeout=10.0)
            payload: Any = response.json() if response.content else None
            return ToolResult(
                tool=self.name,
                action=action,
                summary=f"GET {path} -> {response.status_code}",
                data=payload,
                references=[url],
            )
        except Exception as exc:
            return ToolResult(
                tool=self.name,
                action=action,
                summary=f"API call failed for {path}: {exc}",
                data={"error": str(exc), "url": url},
            )
