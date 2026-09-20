# Support Ticket Agent

An investigation agent that takes a support ticket, queries application logs and user data, checks internal APIs, looks at recent GitHub changes, and returns a root-cause report with a proposed fix.

The workflow matches this loop:

1. **Receive ticket** — understand the issue and extract details  
2. **Plan** — decide tool order (database → API → GitHub → analyze)  
3. **Orchestrator** — call tools, collect evidence, iterate if needed  
4. **Propose a fix** — summarize findings, root cause, code/config change, verification steps  

## Quick start

You need Python 3.9+ and Node 18+.

```powershell
cd C:\documenation\Support-ticket-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt

cd frontend
npm install
```

Start the API (from the repo root, with the venv active):

```powershell
$env:PYTHONPATH = "backend"
python -m uvicorn app.main:app --reload --app-dir backend --port 8000
```

In a second terminal:

```powershell
cd C:\documenation\Support-ticket-agent\frontend
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The sample ticket is already filled in:

> User cannot login to the application. Getting 500 error since yesterday.

Click **Investigate**. The agent will walk the flow diagram live and finish with a report.

CLI (no UI):

```powershell
$env:PYTHONPATH = "backend"
python backend\app\cli.py "User cannot login to the application. Getting 500 error since yesterday." --email jane.doe@acme.com
```

## What the demo shows

The seeded story is a login 500 that started yesterday:

- **Database** — `application_logs` and `users` in SQLite (`data/support_agent.db`)
- **API** — auth-service degraded, ~33% login error rate, `KeyError: 'expires_at'`
- **GitHub** — merged PR #184 / commit `a3f8c21` changed `validate_session` so missing `expires_at` on legacy refresh sessions crashes login
- **Fix** — guard the missing field and keep legacy sessions valid until revoked

No API keys are required for the demo. Optional live backends:

| Variable | Effect |
| --- | --- |
| `OPENAI_API_KEY` | LLM-assisted planning and report writing |
| `GITHUB_TOKEN` + `GITHUB_REPO` | Real GitHub commit/PR search |

Copy `.env.example` to `.env` to set them.

## Project layout

```
backend/app/
  agent/          orchestrator, planner, analyzer
  tools/          database, API, GitHub
  demo/           seeded logs, services, commits
frontend/         live flow UI
```
