from __future__ import annotations

from typing import Literal

import anthropic

SYSTEM_PROMPT = (
    "You are a prompt complexity classifier. "
    "Reply with exactly one word — simple, medium, or hard — "
    "based on the reasoning depth required. No explanation."
)

_VALID_LABELS = {"simple", "medium", "hard"}


def classify(
    prompt: str,
    client: anthropic.Anthropic | None = None,
) -> Literal["simple", "medium", "hard"]:
    """Classify a prompt as simple, medium, or hard using a zero-shot LLM call."""
    if client is None:
        client = anthropic.Anthropic()

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=5,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip().lower()

    if raw not in _VALID_LABELS:
        raise ValueError(f"Unexpected classifier response: {raw!r}")

    return raw  # type: ignore[return-value]
