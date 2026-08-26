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

## What works now (M2)

| Deliverable | Notes |
|-------------|-------|
| `src/classifier/classify.py` | Zero-shot complexity classifier via `claude-haiku-4-5-20251001`; returns `"simple"` / `"medium"` / `"hard"` |
| `src/router/config.py` | `Router` loads `config/routing.yaml` and returns a typed `RouteTarget` dataclass |
| `config/routing.yaml` | Adds `max_cost_usd` guard per tier |
| `tests/test_classifier.py` | 5 unit tests (all mocked — no API key needed) |
| `tests/test_router.py` | 5 unit tests including custom-path fixture |
| `src/` layout with six packages | `classifier`, `router`, `eval`, `api`, `db`, `cli` |
| `pyproject.toml` | Editable install via `pip install -e .`, requires Python ≥ 3.11 |
| `LICENSE` | MIT |
| `.gitignore` | Excludes `.env`, `__pycache__`, `.venv`, SQLite files |

Run tests (no API key required):

```bash
PYTHONPATH=. pytest tests/ -v
```

## Quickstart

> Steps 1–3 work now. The classifier and router (M2) are functional. Step 4 requires M4. Step 5 requires M5.

```bash
# 1. Install dependencies
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

Directories annotated with a future milestone are stubs until that milestone ships. M1 and M2 have shipped.

```
llm-router-eval-bench/
├── config/
│   └── routing.yaml        # complexity → model mapping (Haiku/Sonnet/Opus)
├── data/                   # created in M5
│   └── demo.jsonl          # 30-prompt test suite (M5)
├── src/
│   ├── classifier/         # zero-shot complexity classifier — shipped (M2)
│   ├── router/             # routing table loader — shipped (M2)
│   ├── eval/               # LLM-as-judge rubric engine (M3)
│   ├── api/                # FastAPI /chat endpoint (M4)
│   ├── db/                 # SQLite logging (M4)
│   └── cli/                # Typer CLI — bench run (M5)
├── tests/
│   ├── test_classifier.py  # 5 unit tests, all mocked
│   └── test_router.py      # 5 unit tests including custom-path fixture
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Milestones

| # | Milestone | Status |
|---|-----------|--------|
| M1 | Scaffold + README | done |
| M2 | Complexity classifier + routing table | done |
| M3 | LLM-as-judge rubric engine | pending |
| M4 | FastAPI `/chat` endpoint + SQLite logging | pending |
| M5 | CLI `bench run` + demo dataset + report | pending |

## License

MIT — see [LICENSE](LICENSE).
