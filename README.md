# Agentic Architect Challenge

Three AI systems sharing one foundation (`core/`: config, Gemini client with model failover, embeddings, retrieval, logging).

**Design principle:** decisions that must be reliable — escalation, refund limits, arithmetic — are made in code. The LLM extracts and writes; it never decides whether a limit was crossed.

## How it works

### Part 1 — Email agent (`part1_email_agent/`)

A LangGraph state machine. Any step can hand the email to a human, and an auto-reply is sent only when every check passes.

```
triage → precheck → classify → retrieve → refund_guard → draft_reply → verify → auto_reply
                                                             ↑                │
                                                             └──── redraft ───┘
                      any failed check ──► route_human (ticket + acknowledgement email)
```

- **triage** — drops automated mail (no-reply, mailing lists, own address) to avoid reply loops.
- **precheck** — escalates data loss, outages and security breaches (regex + embedding similarity), and customers with more than 3 contacts in 7 days. Runs before any LLM call.
- **classify** — one or more categories with confidence; low confidence escalates.
- **retrieve** — searches the knowledge-base PDFs; nothing above the similarity floor escalates.
- **refund_guard** — the LLM extracts amount, date and product; policy limits are checked in Python.
- **draft_reply / verify** — drafts with citations, validates them, then runs an independent fact-check. A rejected draft gets one rewrite before escalating.

Every outcome is stored as a ticket (SQLite); a human can answer open tickets from the web UI. Inbox processing is idempotent, so the same email is never answered twice.

### Part 2 — Scraper (`part2_scraper/`)

`naive_scraper.py` is the broken original: no timeout, no status or content-type checks, script and navigation text included, and the whole page sent to the model in one call — which fails past the context window. The fixed pipeline:

```
fetch → extract main content → chunk → map-reduce summarize → length guardrail
```

The guardrail checks the word count, asks for a rewrite quoting the actual count, and truncates at a sentence boundary as a last resort. The web UI refuses non-public URLs (SSRF guard).

### Part 3 — Document agent (`part3_doc_agent/`)

```
route → (retrieve) → (calculate) → respond
```

- **route** — returns the tool decision as a schema; greetings and memory questions use no tool.
- **calculator** — parses expressions with `ast` against a whitelist, never `eval`.
- **memory** — recent turns plus durable facts (name, company, plan), saved per session in `data/part3_sessions/`.

## Setup

### Prerequisites

- **Docker** (recommended), or
- **Python 3.12+** and **Node.js 20+** (for running locally)
- A Gemini API key from <https://aistudio.google.com/apikey> (optional; without a key the system runs on a mock LLM)

### 1. Configure `.env`

```bash
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env`.

### 2a. Run with Docker

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Part 1 — Email agent | <http://localhost:8000> |
| Part 3 — Document chat | <http://localhost:8001> |
| Part 2 — Scraper | <http://localhost:8002> |

If a port is already taken, change `APP_PORT`, `CHAT_PORT`, or `SCRAPER_PORT` in `.env`.

Stop with `docker compose down`.

### 2b. Run locally (without Docker)

```bash
# Virtual environment
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS/Linux

# Python dependencies
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

# Build the Part 1 frontend
cd part1_email_agent/frontend
npm install
npm run build
cd ../..

# Seed demo data and check connectivity
python -m part1_email_agent.cli seed
python -m part1_email_agent.cli health
```

Start each service in its own terminal:

```bash
uvicorn part1_email_agent.web:app --port 8000   # Part 1
uvicorn part3_doc_agent.web:app --port 8001     # Part 3
uvicorn part2_scraper.web:app --port 8002       # Part 2
```

## Tests

```bash
python -m pytest
```

Fully offline (mock LLM and hashing embedder), so no API key is needed.

## Project structure

```
core/                shared foundation
part1_email_agent/   email agent; frontend/ holds the React UI
part2_scraper/       naive script + fixed pipeline
part3_doc_agent/     document chat agent
knowledge_base/      markdown sources and the generated PDFs the agent reads
data/                sample emails and the demo seed script
scripts/             threshold calibration, SMTP end-to-end check
tests/               offline test suite
```
