# llm-router-eval-bench

A local proxy that **routes** LLM prompts to the cheapest model that can handle them and **evaluates** every response with a structured LLM-as-judge rubric — all logged to SQLite.

## What it is

The router classifies each prompt by complexity (simple / medium / hard) and forwards it to the matching model tier (e.g. Haiku → Sonnet → Opus). After the model responds, a lightweight judge scores the answer on three axes (correctness, coherence, conciseness) and writes everything to a local SQLite database. A FastAPI `/chat` endpoint makes the whole stack OpenAI-compatible, so any existing app can point at it without changes.

## Why it exists

Evals are the #1 skill gap in production LLM teams. This project demonstrates: (a) structured eval design, (b) LLM-as-judge methodology, and (c) practical cost/quality trade-off reasoning — all things interviewers at AI-first companies actively probe for.

## Architecture

```
Prompt
  │
  ▼
┌─────────────┐     config/routing.yaml
│  Classifier │──────────────────────────▶ Target Model
│ (zero-shot) │                                 │
└─────────────┘                                 ▼
                                          ┌──────────┐
                                          │  Judge   │──▶ SQLite log
                                          │ (rubric) │
                                          └──────────┘
                                                │
                                                ▼
                                          /chat response
```

**CLI bench flow:**

```
dataset.jsonl ──▶ bench run ──▶ Target Model ──▶ Judge ──▶ SQLite ──▶ report.md
```

## What works now (M1)

The scaffold is in place. All source packages are importable stubs — no logic yet.

| Deliverable | Notes |
|-------------|-------|
| `src/` layout with six packages | `classifier`, `router`, `eval`, `api`, `db`, `cli` — each has an `__init__.py` |
| `config/routing.yaml` | Anthropic model tier mapping: Haiku (simple) → Sonnet (medium) → Opus (hard) |
| `pyproject.toml` | Editable install via `pip install -e .`, requires Python ≥ 3.11 |
| `requirements.txt` | Placeholder — dependencies added per milestone |
| `LICENSE` | MIT |
| `.gitignore` | Excludes `.env`, `__pycache__`, `.venv`, SQLite files |

## Quickstart

> Steps 1–3 work now. Steps 4–5 require M2–M5 to be complete.

```bash
# 1. Install dependencies (currently empty; populated per milestone)
pip install -r requirements.txt

# 2. Install the package in editable mode (required for src/ imports)
pip install -e .

# 3. Set API keys — never commit these
export ANTHROPIC_API_KEY=sk-ant-...
# Or put them in a .env file (see .gitignore — .env is excluded)

# 4. Start the API server  [available after M4]
uvicorn src.api.app:app --reload

# 5. Run a benchmark  [available after M5]
bench run data/demo.jsonl
```

## Project layout

Target layout — directories marked with a milestone exist as stubs only until that milestone ships.

```
llm-router-eval-bench/
├── config/
│   └── routing.yaml        # complexity → model mapping (Haiku/Sonnet/Opus)
├── data/                   # created in M5
│   └── demo.jsonl          # 30-prompt test suite (M5)
├── src/
│   ├── classifier/         # zero-shot complexity classifier (M2)
│   ├── router/             # routing table loader (M2)
│   ├── eval/               # LLM-as-judge rubric engine (M3)
│   ├── api/                # FastAPI /chat endpoint (M4)
│   ├── db/                 # SQLite logging (M4)
│   └── cli/                # Typer CLI — bench run (M5)
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Milestones

| # | Milestone | Status |
|---|-----------|--------|
| M1 | Scaffold + README | done |
| M2 | Complexity classifier + routing table | pending |
| M3 | LLM-as-judge rubric engine | pending |
| M4 | FastAPI `/chat` endpoint + SQLite logging | pending |
| M5 | CLI `bench run` + demo dataset + report | pending |

## License

MIT — see [LICENSE](LICENSE).
