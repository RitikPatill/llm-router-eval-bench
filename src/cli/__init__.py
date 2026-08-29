from __future__ import annotations

import asyncio
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Annotated

import anthropic
import typer
from rich import print as rprint
from rich.progress import track
from rich.table import Table

from db.store import init_db, log_call
from classifier.classify import classify
from eval.judge import judge
from router.config import Router

app = typer.Typer(help="LLM Router Eval Bench CLI")

# Mirror of app.py's _COST_PER_TOKEN — shared util is a M6 concern
_COST_PER_TOKEN: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (0.25e-6, 1.25e-6),
    "claude-sonnet-4-6": (3e-6, 15e-6),
    "claude-opus-4-6": (15e-6, 75e-6),
}


def _token_cost(model: str, input_tok: int, output_tok: int) -> float:
    in_rate, out_rate = _COST_PER_TOKEN.get(model, (0.0, 0.0))
    return input_tok * in_rate + output_tok * out_rate


def _print_table(results: list[dict]) -> None:
    by_model: dict[str, list[dict]] = defaultdict(list)
    for row in results:
        by_model[row["model"]].append(row)

    table = Table(title="Bench Results", show_header=True, header_style="bold cyan")
    table.add_column("Model", style="dim")
    table.add_column("Calls", justify="right")
    table.add_column("Avg Cost ($)", justify="right")
    table.add_column("Avg Score (0–5)", justify="right")
    table.add_column("Avg Latency (ms)", justify="right")

    for model, rows in sorted(by_model.items()):
        calls = len(rows)
        avg_cost = sum(r["cost_usd"] for r in rows) / calls
        avg_score = sum(
            (r["correctness"] + r["coherence"] + r["conciseness"]) / 3 for r in rows
        ) / calls
        avg_latency = sum(r["latency_ms"] for r in rows) / calls
        table.add_row(
            model,
            str(calls),
            f"{avg_cost:.6f}",
            f"{avg_score:.2f}",
            f"{avg_latency:.0f}",
        )

    rprint(table)


def _write_report(results: list[dict], path: Path) -> None:
    by_model: dict[str, list[dict]] = defaultdict(list)
    for row in results:
        by_model[row["model"]].append(row)

    lines = [
        "# Bench Report\n",
        "| Model | Calls | Avg Cost ($) | Avg Score (0–5) | Avg Latency (ms) |",
        "| ----- | ----: | -----------: | --------------: | ---------------: |",
    ]
    for model, rows in sorted(by_model.items()):
        calls = len(rows)
        avg_cost = sum(r["cost_usd"] for r in rows) / calls
        avg_score = sum(
            (r["correctness"] + r["coherence"] + r["conciseness"]) / 3 for r in rows
        ) / calls
        avg_latency = sum(r["latency_ms"] for r in rows) / calls
        lines.append(
            f"| {model} | {calls} | {avg_cost:.6f} | {avg_score:.2f} | {avg_latency:.0f} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    rprint(f"[green]Report written to {path}[/green]")


async def _bench(
    dataset: Path,
    db_path: Path,
    config_path: Path,
    report_path: Path,
) -> None:
    conn = await init_db(db_path)
    router = Router(config_path)
    client = anthropic.Anthropic()

    prompts = []
    with dataset.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                prompts.append(json.loads(line))

    results: list[dict] = []

    for item in track(prompts, description="Running bench..."):
        prompt = item["prompt"]
        try:
            complexity = classify(prompt, client)
            target = router.route(complexity)

            t0 = time.monotonic()
            api_response = client.messages.create(
                model=target.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
            latency_ms = (time.monotonic() - t0) * 1000

            response_text = api_response.content[0].text
            input_tokens = api_response.usage.input_tokens
            output_tokens = api_response.usage.output_tokens

            score = judge(prompt, response_text, client)
            cost = _token_cost(target.model, input_tokens, output_tokens)

            await log_call(
                conn,
                prompt=prompt,
                complexity=complexity,
                model=target.model,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                score=score,
                response=response_text,
            )

            results.append(
                {
                    "model": target.model,
                    "cost_usd": cost,
                    "correctness": score.correctness,
                    "coherence": score.coherence,
                    "conciseness": score.conciseness,
                    "latency_ms": latency_ms,
                }
            )
        except Exception as exc:  # noqa: BLE001
            rprint(f"[yellow]Warning: skipping prompt due to error: {exc}[/yellow]")

    await conn.close()

    if results:
        _print_table(results)
        _write_report(results, report_path)
    else:
        rprint("[red]No results produced — all prompts failed.[/red]")


@app.command()
def run(
    dataset: Annotated[
        Path, typer.Argument(help="JSONL file: {prompt, reference_answer} per line")
    ],
    db: Annotated[Path, typer.Option(help="SQLite DB path")] = Path("bench.db"),
    config: Annotated[Path, typer.Option(help="Routing config YAML")] = Path(
        "config/routing.yaml"
    ),
    report: Annotated[Path, typer.Option(help="Markdown report output")] = Path(
        "report.md"
    ),
) -> None:
    """Replay a JSONL dataset through the router and produce a cost/quality report."""
    if not dataset.exists():
        rprint(f"[red]Error: dataset file not found: {dataset}[/red]")
        raise typer.Exit(code=1)
    asyncio.run(_bench(dataset, db, config, report))
