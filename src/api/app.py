from __future__ import annotations

import asyncio
import time
import uuid
from contextlib import asynccontextmanager

import anthropic
from fastapi import FastAPI, Request

from src.api.models import ChatMessage, ChatRequest, ChatResponse, Choice, Usage
from src.classifier.classify import classify
from src.db.store import init_db, log_call
from src.eval.judge import judge
from src.router.config import Router

# Per-token cost lookup: (input_cost_per_token, output_cost_per_token)
_COST_PER_TOKEN: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (0.25e-6, 1.25e-6),
    "claude-sonnet-4-6": (3e-6, 15e-6),
    "claude-opus-4-6": (15e-6, 75e-6),
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await init_db()
    app.state.router = Router()
    yield
    await app.state.db.close()


app = FastAPI(lifespan=lifespan)


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    # 1. Extract last user message
    user_messages = [m for m in body.messages if m.role == "user"]
    user_prompt = user_messages[-1].content if user_messages else body.messages[-1].content

    # 2. Classify complexity (sync → thread)
    complexity = await asyncio.to_thread(classify, user_prompt)

    # 3. Route to target model
    target = request.app.state.router.route(complexity)

    # 4. Call Anthropic API async
    client = anthropic.AsyncAnthropic()
    kwargs: dict = {
        "model": target.model,
        "max_tokens": body.max_tokens or 1024,
        "messages": [{"role": m.role, "content": m.content} for m in body.messages],
    }
    if body.temperature is not None:
        kwargs["temperature"] = body.temperature

    t0 = time.monotonic()
    api_response = await client.messages.create(**kwargs)
    latency_ms = (time.monotonic() - t0) * 1000

    response_text = api_response.content[0].text
    input_tokens = api_response.usage.input_tokens
    output_tokens = api_response.usage.output_tokens

    # 5. Judge the response (sync → thread)
    score = await asyncio.to_thread(judge, user_prompt, response_text)

    # 6. Compute cost
    in_rate, out_rate = _COST_PER_TOKEN.get(target.model, (0.0, 0.0))
    cost_usd = input_tokens * in_rate + output_tokens * out_rate

    # 7. Log to DB
    await log_call(
        request.app.state.db,
        prompt=user_prompt,
        complexity=complexity,
        model=target.model,
        latency_ms=latency_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        score=score,
        response=response_text,
    )

    # 8. Return OpenAI-compatible response
    return ChatResponse(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        model=target.model,
        choices=[
            Choice(
                index=0,
                message=ChatMessage(role="assistant", content=response_text),
                finish_reason="stop",
            )
        ],
        usage=Usage(
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        ),
    )
