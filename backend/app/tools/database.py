from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.demo.seed import connect, seed
from app.models import ToolResult


def _rows(cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cursor.fetchall()]


class DatabaseTool:
    name = "database"

    def __init__(self) -> None:
        seed()

    def search_logs(
        self,
        keywords: list[str] | None = None,
        status_code: int | None = None,
        hours: int = 36,
        path: str | None = None,
    ) -> ToolResult:
        conn = connect()
        try:
            since = (
                (datetime.now(timezone.utc) - timedelta(hours=hours))
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )
            sql = "SELECT * FROM application_logs WHERE ts >= ?"
            params: list[Any] = [since]
            if status_code is not None:
                sql += " AND status_code = ?"
                params.append(status_code)
            if path:
                sql += " AND path LIKE ?"
                params.append(f"%{path}%")
            if keywords:
                clauses = []
                for word in keywords:
                    clauses.append(
                        "(lower(message) LIKE ? OR lower(path) LIKE ? "
                        "OR lower(COALESCE(error_signature, '')) LIKE ? "
                        "OR lower(COALESCE(user_email, '')) LIKE ?)"
                    )
                    like = f"%{word.lower()}%"
                    params.extend([like, like, like, like])
                sql += " AND (" + " OR ".join(clauses) + ")"
            sql += " ORDER BY ts DESC LIMIT 25"
            rows = _rows(conn.execute(sql, params))
        finally:
            conn.close()

        errors = [r for r in rows if r["status_code"] >= 500]
        summary = (
            f"Found {len(rows)} log rows in the last {hours}h"
            + (f" with status {status_code}" if status_code else "")
            + (f", including {len(errors)} server errors." if errors else ".")
        )
        if errors:
            top = errors[0]
            summary += f" Latest: {top['error_signature']} on {top['path']} ({top['ts']})."
        return ToolResult(
            tool=self.name,
            action="search_logs",
            summary=summary,
            data={"since": since, "count": len(rows), "rows": rows},
            references=[f"db:application_logs#{row['id']}" for row in rows[:8]],
        )

    def get_user(self, email: str) -> ToolResult:
        conn = connect()
        try:
            user = conn.execute(
                "SELECT * FROM users WHERE lower(email) = lower(?)", (email,)
            ).fetchone()
            recent = _rows(
                conn.execute(
                    """
                    SELECT * FROM application_logs
                    WHERE lower(user_email) = lower(?)
                    ORDER BY ts DESC LIMIT 8
                    """,
                    (email,),
                )
            )
        finally:
            conn.close()

        if not user:
            return ToolResult(
                tool=self.name,
                action="get_user",
                summary=f"No user found for {email}.",
                data={"email": email, "user": None, "recent_logs": []},
            )
        user_dict = dict(user)
        return ToolResult(
            tool=self.name,
            action="get_user",
            summary=(
                f"User {user_dict['name']} ({user_dict['email']}) is {user_dict['status']}, "
                f"session_type={user_dict['session_type']}, last_login={user_dict['last_login_at']}."
            ),
            data={"user": user_dict, "recent_logs": recent},
            references=[f"db:users#{user_dict['id']}"],
        )

    def related_errors(self, signature: str) -> ToolResult:
        conn = connect()
        try:
            rows = _rows(
                conn.execute(
                    """
                    SELECT error_signature, path, COUNT(*) AS count,
                           MIN(ts) AS first_seen, MAX(ts) AS last_seen
                    FROM application_logs
                    WHERE error_signature LIKE ?
                    GROUP BY error_signature, path
                    ORDER BY count DESC
                    """,
                    (f"%{signature}%",),
                )
            )
        finally:
            conn.close()
        total = sum(r["count"] for r in rows)
        summary = (
            f"Grouped {total} matching errors for '{signature}'."
            if rows
            else f"No related errors for '{signature}'."
        )
        return ToolResult(
            tool=self.name,
            action="related_errors",
            summary=summary,
            data={"signature": signature, "groups": rows},
            references=[f"db:error_signature:{signature}"],
        )
