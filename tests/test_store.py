import hashlib

import pytest

from src.db import init_db, log_call
from src.eval import RubricScore


@pytest.fixture
async def conn(tmp_path):
    db_path = tmp_path / "test.db"
    connection = await init_db(db_path)
    yield connection
    await connection.close()


async def test_init_db_creates_table(conn):
    async with conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='calls'"
    ) as cursor:
        row = await cursor.fetchone()
    assert row is not None
    assert row[0] == "calls"


async def test_log_call_inserts_row(conn):
    score = RubricScore(correctness=4, coherence=5, conciseness=3)
    rowid = await log_call(
        conn,
        prompt="What is 2+2?",
        complexity="simple",
        model="claude-haiku-4-5-20251001",
        latency_ms=120.5,
        input_tokens=10,
        output_tokens=5,
        cost_usd=0.000012,
        score=score,
        response="4",
    )
    assert rowid == 1

    async with conn.execute("SELECT * FROM calls WHERE id = ?", (rowid,)) as cursor:
        row = await cursor.fetchone()

    assert row is not None
    # columns: id, created_at, prompt_hash, complexity, model, latency_ms,
    #          input_tokens, output_tokens, cost_usd,
    #          correctness, coherence, conciseness, prompt, response
    assert row[2] == hashlib.sha256("What is 2+2?".encode()).hexdigest()
    assert row[3] == "simple"
    assert row[4] == "claude-haiku-4-5-20251001"
    assert row[5] == 120.5
    assert row[6] == 10
    assert row[7] == 5
    assert row[8] == pytest.approx(0.000012)
    assert row[9] == 4   # correctness
    assert row[10] == 5  # coherence
    assert row[11] == 3  # conciseness
    assert row[12] == "What is 2+2?"
    assert row[13] == "4"


async def test_log_call_two_rows_distinct_ids(conn):
    score = RubricScore(correctness=3, coherence=3, conciseness=3)
    id1 = await log_call(
        conn,
        prompt="First prompt",
        complexity="simple",
        model="claude-haiku-4-5-20251001",
        latency_ms=100.0,
        input_tokens=8,
        output_tokens=4,
        cost_usd=0.000008,
        score=score,
        response="First response",
    )
    id2 = await log_call(
        conn,
        prompt="Second prompt",
        complexity="medium",
        model="claude-sonnet-4-6",
        latency_ms=200.0,
        input_tokens=15,
        output_tokens=10,
        cost_usd=0.000025,
        score=score,
        response="Second response",
    )
    assert id1 != id2
