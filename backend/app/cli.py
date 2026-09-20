from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models import TicketRequest
from app.agent.orchestrator import run_investigation


async def _run(ticket: str, email: str | None) -> None:
    async for event in run_investigation(TicketRequest(ticket=ticket, reporter_email=email)):
        print(f"[{event.stage}] {event.title}")
        if event.type == "report_ready":
            print("\n=== FINAL REPORT ===")
            print(json.dumps(event.detail, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Investigate a support ticket")
    parser.add_argument("ticket", nargs="?", help="Ticket text")
    parser.add_argument("--email", help="Optional reporter email")
    args = parser.parse_args()
    ticket = args.ticket or (
        "User cannot login to the application. Getting 500 error since yesterday."
    )
    asyncio.run(_run(ticket, args.email))


if __name__ == "__main__":
    main()
