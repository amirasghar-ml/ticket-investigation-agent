"""Demo application data that the tools query.

The seeded story matches the example ticket in the flow diagram:

  "User cannot login to the application. Getting 500 error since yesterday."

Yesterday's auth deploy introduced a KeyError on missing `expires_at` for
legacy refresh sessions. Login started returning HTTP 500.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

NOW = datetime.now(timezone.utc)
YESTERDAY = NOW - timedelta(days=1)
TWO_DAYS_AGO = NOW - timedelta(days=2)
DEPLOY_AT = YESTERDAY.replace(hour=9, minute=12, second=0, microsecond=0)


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


USERS = [
    {
        "id": 1042,
        "email": "jane.doe@acme.com",
        "name": "Jane Doe",
        "status": "active",
        "last_login_at": iso(TWO_DAYS_AGO.replace(hour=18, minute=4)),
        "session_type": "legacy_refresh",
        "created_at": "2024-03-11T08:00:00Z",
    },
    {
        "id": 881,
        "email": "sam.lee@acme.com",
        "name": "Sam Lee",
        "status": "active",
        "last_login_at": iso(NOW - timedelta(hours=3)),
        "session_type": "standard",
        "created_at": "2023-11-02T14:22:00Z",
    },
]

TRACEBACK = (
    "Traceback (most recent call last):\n"
    '  File "app/api/auth.py", line 41, in login\n'
    "    session = validate_session(refresh_token)\n"
    '  File "app/auth/session.py", line 87, in validate_session\n'
    '    expires = datetime.fromisoformat(token["expires_at"])\n'
    "KeyError: 'expires_at'"
)

APPLICATION_LOGS = [
    {
        "id": 9001,
        "ts": iso(DEPLOY_AT + timedelta(minutes=18)),
        "level": "ERROR",
        "service": "auth-service",
        "path": "/api/auth/login",
        "status_code": 500,
        "user_email": "jane.doe@acme.com",
        "message": "Login failed with unhandled KeyError in validate_session",
        "error_signature": "KeyError: 'expires_at'",
        "stack_trace": TRACEBACK,
        "request_id": "req_7f3a91",
    },
    {
        "id": 9002,
        "ts": iso(DEPLOY_AT + timedelta(hours=2, minutes=4)),
        "level": "ERROR",
        "service": "auth-service",
        "path": "/api/auth/login",
        "status_code": 500,
        "user_email": "priya.nair@acme.com",
        "message": "Login failed with unhandled KeyError in validate_session",
        "error_signature": "KeyError: 'expires_at'",
        "stack_trace": TRACEBACK,
        "request_id": "req_8c12ab",
    },
    {
        "id": 9003,
        "ts": iso(NOW - timedelta(hours=6)),
        "level": "ERROR",
        "service": "auth-service",
        "path": "/api/auth/login",
        "status_code": 500,
        "user_email": "jane.doe@acme.com",
        "message": "Login failed with unhandled KeyError in validate_session",
        "error_signature": "KeyError: 'expires_at'",
        "stack_trace": TRACEBACK,
        "request_id": "req_9aa001",
    },
    {
        "id": 9004,
        "ts": iso(NOW - timedelta(hours=2)),
        "level": "ERROR",
        "service": "auth-service",
        "path": "/api/auth/login",
        "status_code": 500,
        "user_email": "omar.hassan@acme.com",
        "message": "Login failed with unhandled KeyError in validate_session",
        "error_signature": "KeyError: 'expires_at'",
        "stack_trace": TRACEBACK,
        "request_id": "req_bb21c0",
    },
    {
        "id": 8001,
        "ts": iso(TWO_DAYS_AGO),
        "level": "INFO",
        "service": "auth-service",
        "path": "/api/auth/login",
        "status_code": 200,
        "user_email": "jane.doe@acme.com",
        "message": "Login succeeded",
        "error_signature": None,
        "stack_trace": None,
        "request_id": "req_ok_441",
    },
    {
        "id": 7100,
        "ts": iso(NOW - timedelta(hours=8)),
        "level": "WARN",
        "service": "payments-service",
        "path": "/api/checkout",
        "status_code": 429,
        "user_email": "sam.lee@acme.com",
        "message": "Rate limit exceeded for checkout attempts",
        "error_signature": "RateLimitError",
        "stack_trace": None,
        "request_id": "req_pay_12",
    },
]

ERROR_METRICS = {
    "window": "last_24h",
    "path": "/api/auth/login",
    "total_requests": 1840,
    "error_count": 612,
    "error_rate": 0.332,
    "status_breakdown": {"200": 1228, "500": 612},
    "first_seen": iso(DEPLOY_AT + timedelta(minutes=16)),
    "top_error": "KeyError: 'expires_at'",
}

SERVICE_STATUS = [
    {
        "name": "auth-service",
        "status": "degraded",
        "version": "2.14.1",
        "deployed_at": iso(DEPLOY_AT),
        "error_rate_5m": 0.31,
        "notes": "Elevated 500s on POST /api/auth/login since the 2.14.1 deploy.",
    },
    {
        "name": "api-gateway",
        "status": "healthy",
        "version": "1.9.0",
        "deployed_at": iso(NOW - timedelta(days=12)),
        "error_rate_5m": 0.004,
        "notes": "Passing through auth 500s; gateway itself is healthy.",
    },
    {
        "name": "payments-service",
        "status": "healthy",
        "version": "3.2.0",
        "deployed_at": iso(NOW - timedelta(days=4)),
        "error_rate_5m": 0.01,
        "notes": None,
    },
]

BUGGY_CODE = '''def validate_session(token: dict) -> bool:
    """Return True when the refresh/session token is still valid."""
    if token.get("revoked"):
        return False
    expires = datetime.fromisoformat(token["expires_at"])
    return expires > datetime.utcnow()
'''

FIXED_CODE = '''def validate_session(token: dict) -> bool:
    """Return True when the refresh/session token is still valid."""
    if token.get("revoked"):
        return False
    expires_at = token.get("expires_at")
    if not expires_at:
        # Legacy refresh sessions omit expiry. Treat as valid until revoked.
        return True
    expires = datetime.fromisoformat(expires_at)
    return expires > datetime.utcnow()
'''

GITHUB_COMMITS = [
    {
        "sha": "a3f8c21d9b",
        "html_url": "https://github.com/acme/webapp/commit/a3f8c21d9b",
        "message": "Harden JWT expiry handling in validate_session",
        "author": "alex.kim",
        "committed_at": iso(DEPLOY_AT - timedelta(minutes=40)),
        "files": ["app/auth/session.py", "app/api/auth.py"],
        "diff": (
            "--- a/app/auth/session.py\n"
            "+++ b/app/auth/session.py\n"
            "@@ def validate_session(token):\n"
            "-    expires = token.get('exp') or token.get('expires_at')\n"
            "-    if not expires:\n"
            "-        return not token.get('revoked', False)\n"
            "+    expires = datetime.fromisoformat(token['expires_at'])\n"
            "+    return expires > datetime.utcnow()\n"
        ),
        "relevance": "high",
    },
    {
        "sha": "b71e04aa12",
        "html_url": "https://github.com/acme/webapp/commit/b71e04aa12",
        "message": "Add structured logging around auth login handler",
        "author": "morgan.wei",
        "committed_at": iso(NOW - timedelta(days=6)),
        "files": ["app/api/auth.py"],
        "diff": (
            "--- a/app/api/auth.py\n"
            "+++ b/app/api/auth.py\n"
            "+    logger.info('login_attempt', extra={'email': email})\n"
        ),
        "relevance": "medium",
    },
    {
        "sha": "c90dd118fe",
        "html_url": "https://github.com/acme/webapp/commit/c90dd118fe",
        "message": "Tune checkout rate limiter",
        "author": "sam.lee",
        "committed_at": iso(NOW - timedelta(days=3)),
        "files": ["app/payments/limiter.py"],
        "diff": "--- a/app/payments/limiter.py\n+LIMIT = 30\n",
        "relevance": "low",
    },
]

GITHUB_PRS = [
    {
        "number": 184,
        "title": "Harden JWT expiry handling",
        "html_url": "https://github.com/acme/webapp/pull/184",
        "state": "merged",
        "merged_at": iso(DEPLOY_AT - timedelta(minutes=25)),
        "author": "alex.kim",
        "body": (
            "Require expires_at on session tokens so expired JWTs cannot be reused. "
            "Follow-up needed for legacy refresh sessions that still omit the field."
        ),
        "files": ["app/auth/session.py"],
        "commit_sha": "a3f8c21d9b",
    },
    {
        "number": 176,
        "title": "Improve login observability",
        "html_url": "https://github.com/acme/webapp/pull/176",
        "state": "merged",
        "merged_at": iso(NOW - timedelta(days=6)),
        "author": "morgan.wei",
        "body": "Add request IDs and structured logs to the login endpoint.",
        "files": ["app/api/auth.py"],
        "commit_sha": "b71e04aa12",
    },
]
