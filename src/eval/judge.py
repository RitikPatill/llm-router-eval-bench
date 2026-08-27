from __future__ import annotations

import json
from dataclasses import dataclass

import anthropic

SYSTEM_PROMPT = (
    "You are an objective evaluator. "
    "Given a user prompt and an AI response, score the response on three axes. "
    "Reply with ONLY a JSON object, no prose, no markdown fences:\n"
    '{"correctness": <int 0-5>, "coherence": <int 0-5>, "conciseness": <int 0-5>}'
)


@dataclass
class RubricScore:
    correctness: int  # 0–5
    coherence: int    # 0–5
    conciseness: int  # 0–5


def judge(
    prompt: str,
    response: str,
    client: anthropic.Anthropic | None = None,
    model: str = "claude-haiku-4-5-20251001",
) -> RubricScore:
    """Call a judge model and return a RubricScore for the given (prompt, response) pair."""
    if client is None:
        client = anthropic.Anthropic()

    user_message = f"Prompt: {prompt}\n\nResponse: {response}"

    result = client.messages.create(
        model=model,
        max_tokens=64,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw = result.content[0].text.strip()

    try:
        parsed = json.loads(raw)
        correctness = int(parsed["correctness"])
        coherence = int(parsed["coherence"])
        conciseness = int(parsed["conciseness"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Judge returned unparseable response: {raw!r}") from exc

    for name, val in [("correctness", correctness), ("coherence", coherence), ("conciseness", conciseness)]:
        if not (0 <= val <= 5):
            raise ValueError(f"Score '{name}' out of range [0, 5]: {val}")

    return RubricScore(correctness=correctness, coherence=coherence, conciseness=conciseness)
