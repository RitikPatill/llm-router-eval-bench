from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from src.eval.judge import RubricScore

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS calls (
    id             INTEGER PRIMARY KEY,
    created_at     TEXT    NOT NULL,
    prompt_hash    TEXT    NOT NULL,
    complexity     TEXT    NOT NULL,
    model          TEXT    NOT NULL,
    latency_ms     REAL    NOT NULL,
    input_tokens   INTEGER NOT NULL,
    output_tokens  INTEGER NOT NULL,
    cost_usd       REAL    NOT NULL,
    correctness    INTEGER NOT NULL,
    coherence      INTEGER NOT NULL,
    conciseness    INTEGER NOT NULL,
    prompt         TEXT    NOT NULL,
    response       TEXT    NOT NULL
)
"""


async def init_db(path: str | Path = "router.db") -> aiosqlite.Connection:
    """Open (creating if needed) the DB and ensure the schema exists. Returns the connection."""
    conn = await aiosqlite.connect(str(path))
    await conn.execute(_CREATE_TABLE)
    await conn.commit()
    return conn


async def log_call(
    conn: aiosqlite.Connection,
    *,
    prompt: str,
    complexity: str,
    model: str,
    latency_ms: float,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    score: RubricScore,
    response: str,
) -> int:
    """Insert one record and return its rowid."""
    prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
    created_at = datetime.now(timezone.utc).isoformat()

    cursor = await conn.execute(
        """
        INSERT INTO calls
            (created_at, prompt_hash, complexity, model,
             latency_ms, input_tokens, output_tokens, cost_usd,
             correctness, coherence, conciseness, prompt, response)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            created_at,
            prompt_hash,
            complexity,
            model,
            latency_ms,
            input_tokens,
            output_tokens,
            cost_usd,
            score.correctness,
            score.coherence,
            score.conciseness,
            prompt,
            response,
        ),
    )
    await conn.commit()
    return cursor.lastrowid
