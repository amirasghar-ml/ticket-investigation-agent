from __future__ import annotations

import json
from typing import Any

from app.config import settings


def llm_enabled() -> bool:
    return bool(settings.openai_api_key)


def complete_json(system: str, user: str) -> dict[str, Any] | None:
    """Ask the configured LLM for a JSON object. Returns None if unused or failed."""
    if not llm_enabled():
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
        response = client.chat.completions.create(
            model=settings.openai_model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None
