from app.agent.planner import build_plan
from app.demo.seed import seed
from app.models import TicketRequest
from app.tools.database import DatabaseTool


def test_seed_and_login_logs():
    seed()
    result = DatabaseTool().search_logs(keywords=["login"], status_code=500, hours=48, path="/api/auth/login")
    assert result.data["count"] >= 1
    assert any("expires_at" in (row.get("error_signature") or "") for row in result.data["rows"])


def test_plan_for_sample_ticket():
    plan = build_plan("User cannot login to the application. Getting 500 error since yesterday.")
    assert plan.extracted.feature == "login"
    assert plan.extracted.error_code == "500"
    assert [step.tool for step in plan.steps][:3] == ["database", "api", "github"]


def test_full_investigation():
    import asyncio
    from app.agent.orchestrator import run_investigation

    async def _run():
        report = None
        async for event in run_investigation(
            TicketRequest(
                ticket="User cannot login to the application. Getting 500 error since yesterday.",
                reporter_email="jane.doe@acme.com",
            )
        ):
            if event.type == "report_ready":
                report = event.detail
        return report

    report = asyncio.run(_run())
    assert report is not None
    assert "expires_at" in report["root_cause"]
    assert report["proposed_fix"]["file_path"] == "app/auth/session.py"


def test_seed_and_login_logs():
    seed()
    result = DatabaseTool().search_logs(keywords=["login"], status_code=500, hours=48, path="/api/auth/login")
    assert result.data["count"] >= 1
    assert any("expires_at" in (row.get("error_signature") or "") for row in result.data["rows"])


def test_plan_for_sample_ticket():
    plan = build_plan("User cannot login to the application. Getting 500 error since yesterday.")
    assert plan.extracted.feature == "login"
    assert plan.extracted.error_code == "500"
    assert [step.tool for step in plan.steps][:3] == ["database", "api", "github"]
