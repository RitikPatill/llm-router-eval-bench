from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.db.store import init_db
from src.eval.judge import RubricScore


def _make_anthropic_response(text: str = "Hello!", input_tokens: int = 10, output_tokens: int = 5):
    """Build a mock Anthropic API response object."""
    content_block = MagicMock()
    content_block.text = text

    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    response = MagicMock()
    response.content = [content_block]
    response.usage = usage
    return response


@pytest.fixture()
async def client(tmp_path):
    """Set up patched app state and yield an httpx AsyncClient."""
    fake_score = RubricScore(correctness=4, coherence=5, conciseness=3)
    fake_response = _make_anthropic_response()

    mock_route_target = MagicMock()
    mock_route_target.model = "claude-haiku-4-5-20251001"

    mock_router = MagicMock()
    mock_router.route.return_value = mock_route_target

    mock_anthropic_instance = AsyncMock()
    mock_anthropic_instance.messages.create = AsyncMock(return_value=fake_response)

    # Set app.state directly — ASGITransport does not run the lifespan
    db = await init_db(str(tmp_path / "test.db"))
    app.state.db = db
    app.state.router = mock_router

    with (
        patch("src.api.app.classify", return_value="simple") as mock_classify,
        patch("src.api.app.anthropic.AsyncAnthropic", return_value=mock_anthropic_instance),
        patch("src.api.app.judge", return_value=fake_score) as mock_judge,
        patch("src.api.app.log_call", new_callable=AsyncMock) as mock_log,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac, {
                "classify": mock_classify,
                "router": mock_router,
                "judge": mock_judge,
                "log_call": mock_log,
            }

    await db.close()


async def test_chat_returns_200(client):
    ac, _ = client
    resp = await ac.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] != ""
    assert data["object"] == "chat.completion"


async def test_chat_logs_to_db(client):
    ac, mocks = client
    resp = await ac.post("/chat", json={"messages": [{"role": "user", "content": "hi"}]})
    assert resp.status_code == 200

    mocks["log_call"].assert_called_once()
    call_kwargs = mocks["log_call"].call_args.kwargs
    assert call_kwargs["complexity"] == "simple"
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_kwargs["latency_ms"] >= 0


async def test_chat_missing_messages_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/chat", json={})
    assert resp.status_code == 422
