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

## What works now (M5)

| Deliverable | Notes |
|-------------|-------|
| `src/cli/__init__.py` | Typer CLI with `bench run` command — replays a JSONL dataset through the full pipeline (classify → route → Anthropic → judge → SQLite), prints a Rich table per model, writes `report.md` |
| `data/demo.jsonl` | 30-prompt demo dataset: 10 simple / 10 medium / 10 hard prompts with `complexity_hint` metadata |
| `src/api/app.py` | FastAPI app with `POST /chat` (OpenAI-compatible); wires classifier → router → Anthropic API → judge → SQLite in one request |
| `src/api/models.py` | Pydantic models: `ChatRequest`, `ChatResponse`, `Choice`, `Usage`, `ChatMessage` |
| `src/classifier/classify.py` | Zero-shot complexity classifier via `claude-haiku-4-5-20251001`; returns `"simple"` / `"medium"` / `"hard"` |
| `src/router/config.py` | `Router` loads `config/routing.yaml` and returns a typed `RouteTarget` dataclass |
| `config/routing.yaml` | `max_cost_usd` guard per tier |
| `src/eval/judge.py` | LLM-as-judge engine — scores `(prompt, response)` pairs; returns `RubricScore(correctness, coherence, conciseness)` (each 0–5) |
| `src/db/store.py` | `init_db()` / `log_call()` via `aiosqlite` — persists prompt hash, model, latency, tokens, cost, rubric scores |

Run all tests (no API key required):

```bash
PYTHONPATH=. pytest tests/ -v
# 25 passed
```

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Install the package in editable mode (registers the `bench` CLI command)
pip install -e .

# 3. Set API keys — never commit these
export ANTHROPIC_API_KEY=sk-ant-...
# Or put them in a .env file (see .gitignore — .env is excluded)

# 4. Start the API server
uvicorn src.api.app:app --reload

# 5. Call the endpoint (OpenAI-compatible shape)
curl http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "What is 2+2?"}]}'

# 6. Run a benchmark against the 30-prompt demo dataset
bench run data/demo.jsonl

# Optional flags
bench run data/demo.jsonl --db my.db --config config/routing.yaml --report report.md
```

### Bench output

```
Running bench... ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100% 30/30
          Bench Results
┌──────────────────────────┬───────┬──────────────┬─────────────────┬──────────────────┐
│ Model                    │ Calls │  Avg Cost ($) │ Avg Score (0–5) │ Avg Latency (ms) │
├──────────────────────────┼───────┼──────────────┼─────────────────┼──────────────────┤
│ claude-haiku-4-5-20251001│    10 │     0.000023 │            4.12 │              620 │
│ claude-sonnet-4-6        │    10 │     0.000890 │            4.51 │             1340 │
│ claude-opus-4-6          │    10 │     0.004200 │            4.78 │             2800 │
└──────────────────────────┴───────┴──────────────┴─────────────────┴──────────────────┘
Report written to report.md
```

## Project layout

All milestones M1–M5 have shipped.

```
llm-router-eval-bench/
├── config/
│   └── routing.yaml        # complexity → model mapping (Haiku/Sonnet/Opus)
├── data/                   # created in M5
│   └── demo.jsonl          # 30-prompt test suite (M5)
├── src/
│   ├── classifier/         # zero-shot complexity classifier — shipped (M2)
│   ├── router/             # routing table loader — shipped (M2)
│   ├── eval/               # LLM-as-judge rubric engine — shipped (M3)
│   ├── db/                 # SQLite logging — shipped (M3)
│   ├── api/                # FastAPI /chat endpoint — shipped (M4)
│   └── cli/                # Typer CLI — bench run (M5)
├── tests/
│   ├── test_classifier.py  # 5 unit tests, all mocked
│   ├── test_router.py      # 5 unit tests including custom-path fixture
│   ├── test_judge.py       # 6 unit tests for judge(), all mocked
│   ├── test_store.py       # 3 async unit tests for SQLite persistence
│   ├── test_api.py         # 3 async tests for POST /chat
│   └── test_cli.py         # 3 unit tests for bench run CLI
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Milestones

| # | Milestone | Status |
|---|-----------|--------|
| M1 | Scaffold + README | done |
| M2 | Complexity classifier + routing table | done |
| M3 | LLM-as-judge rubric engine + SQLite store | done |
| M4 | FastAPI `/chat` endpoint | done |
| M5 | CLI `bench run` + demo dataset + report | done |

## License

MIT — see [LICENSE](LICENSE).
