from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from typer.testing import CliRunner

from src.cli import app

runner = CliRunner()


def _make_anthropic_client(response_text: str = "42", input_tokens: int = 10, output_tokens: int = 5):
    """Return a mock anthropic.Anthropic() whose messages.create behaves correctly."""
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    content = MagicMock()
    content.text = response_text

    api_response = MagicMock()
    api_response.content = [content]
    api_response.usage = usage

    client = MagicMock()
    client.messages.create.return_value = api_response
    return client


def _make_score(correctness=4, coherence=4, conciseness=4):
    score = MagicMock()
    score.correctness = correctness
    score.coherence = coherence
    score.conciseness = conciseness
    return score


def _write_dataset(tmp_path: Path, rows: list[dict]) -> Path:
    ds = tmp_path / "test.jsonl"
    ds.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return ds


# ---------------------------------------------------------------------------
# 1. Happy-path: 2-row JSONL, all patches in place
# ---------------------------------------------------------------------------

def test_bench_run_happy_path(tmp_path, mocker):
    rows = [
        {"prompt": "What is 2+2?", "reference_answer": "4", "complexity_hint": "simple"},
        {"prompt": "Explain recursion.", "reference_answer": "A function that calls itself.", "complexity_hint": "medium"},
    ]
    ds = _write_dataset(tmp_path, rows)

    mocker.patch("src.cli.classify", return_value="simple")
    mocker.patch("src.cli.judge", return_value=_make_score())
    mocker.patch("src.cli.init_db", new=AsyncMock(return_value=AsyncMock()))
    mocker.patch("src.cli.log_call", new=AsyncMock())
    mocker.patch("src.cli.anthropic.Anthropic", return_value=_make_anthropic_client())

    result = runner.invoke(app, ["run", str(ds), "--db", str(tmp_path / "bench.db")])
    assert result.exit_code == 0, result.output
    assert "Model" in result.output


# ---------------------------------------------------------------------------
# 2. Missing dataset file → non-zero exit code
# ---------------------------------------------------------------------------

def test_bench_run_missing_file(tmp_path):
    missing = tmp_path / "does_not_exist.jsonl"
    result = runner.invoke(app, ["run", str(missing)])
    assert result.exit_code != 0 or "not found" in result.output.lower() or "error" in result.output.lower()


# ---------------------------------------------------------------------------
# 3. Happy-path + verify report.md is written with Markdown table header
# ---------------------------------------------------------------------------

def test_bench_writes_report(tmp_path, mocker):
    rows = [
        {"prompt": "What is 2+2?", "reference_answer": "4", "complexity_hint": "simple"},
    ]
    ds = _write_dataset(tmp_path, rows)
    report_path = tmp_path / "report.md"

    mocker.patch("src.cli.classify", return_value="simple")
    mocker.patch("src.cli.judge", return_value=_make_score())
    mocker.patch("src.cli.init_db", new=AsyncMock(return_value=AsyncMock()))
    mocker.patch("src.cli.log_call", new=AsyncMock())
    mocker.patch("src.cli.anthropic.Anthropic", return_value=_make_anthropic_client())

    result = runner.invoke(
        app,
        ["run", str(ds), "--db", str(tmp_path / "bench.db"), "--report", str(report_path)],
    )
    assert result.exit_code == 0, result.output
    assert report_path.exists(), "report.md was not created"
    content = report_path.read_text(encoding="utf-8")
    assert "| Model |" in content
