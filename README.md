# TriAgent

Three AI agents on one shared core (`core/`: provider-agnostic LLM client with
model/provider failover, embeddings, retrieval, logging).

The LLM layer auto-detects the provider from the API key you put in `.env`, so
the same code works with DeepSeek, OpenAI, Anthropic, Gemini, OpenRouter, Groq,
Mistral, Together, Fireworks, local Ollama/LM Studio, or any OpenAI-compatible
endpoint.

**Design principle:** decisions that must be reliable — escalation, refund
limits, arithmetic — are made in code. The LLM extracts and writes; it never
decides whether a limit was crossed.

| Module | What it does | Default URL |
|---|---|---|
| **Mail** — email agent | Answers support email or escalates to a human | <http://localhost:8000> |
| **Lens** — scrape & summarize | Fetches a page, extracts the main content, summarizes it safely | <http://localhost:8002> |
| **Docs** — document chat | Grounded Q&A over one handbook, with per-session memory | <http://localhost:8001> |

All three are served by one React app in `frontend/`. Open any of the three
ports and use the tabs to switch modules; the same bundle is injected with a
different default tab and the companion ports.

## How it works

### Mail — email agent (`part1_email_agent/`)

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

### Lens — scraper (`part2_scraper/`)

`naive_scraper.py` is the broken original: no timeout, no status or content-type checks, script and navigation text included, and the whole page sent to the model in one call — which is expensive, lower quality on large pages, and can fail past the context window. The fixed pipeline:

```
fetch → extract main content → chunk → map-reduce summarize → length guardrail
```

The guardrail checks the word count, asks for a rewrite quoting the actual count, and truncates at a sentence boundary as a last resort. The web UI refuses non-public URLs (SSRF guard).

### Docs — document agent (`part3_doc_agent/`)

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
- One LLM API key from any supported provider (optional; without a key the
  system runs on a deterministic mock LLM). DeepSeek is the documented default:
  <https://platform.deepseek.com/api_keys>

### 1. Configure `.env`

```bash
cp .env.example .env
```

Open `.env` and fill **one** provider key. TriAgent auto-detects which provider
to use from the key that is present:

```env
# DeepSeek example
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_MODEL=deepseek-flash
```

You do not need to set `LLM_PROVIDER` when only one key is filled. If you fill
more than one key, choose the active provider explicitly:

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
```

`.env` is ignored by git. `.env.example` is the safe template and contains a
slot for every supported provider.

### Supported LLM providers

| Provider | Env key | Notes |
|---|---|---|
| **DeepSeek** | `DEEPSEEK_API_KEY` | default example; `deepseek-flash` |
| **OpenAI** | `OPENAI_API_KEY` | set `OPENAI_MODEL` |
| **Anthropic** | `ANTHROPIC_API_KEY` | native Claude adapter |
| **Google Gemini** | `GEMINI_API_KEY` | OpenAI-compatible endpoint |
| **OpenRouter** | `OPENROUTER_API_KEY` | one key for many models |
| **Groq** | `GROQ_API_KEY` | set `GROQ_MODEL` |
| **Mistral** | `MISTRAL_API_KEY` | `mistral-small-latest` default |
| **Together** | `TOGETHER_API_KEY` | set `TOGETHER_MODEL` |
| **Fireworks** | `FIREWORKS_API_KEY` | set `FIREWORKS_MODEL` |
| **Ollama / LM Studio** | no key | set `LLM_PROVIDER=ollama` or `lmstudio` |
| **Any OpenAI-compatible API** | `LLM_API_KEY` | set `LLM_PROVIDER=custom`, `LLM_BASE_URL`, `LLM_MODEL` |

If you set `LLM_BASE_URL` and `LLM_MODEL` for a custom endpoint, also set
`LLM_PROVIDER=custom`; otherwise auto-detection may see those values as a second
provider when another API key is present.

Optional controls:

```env
LLM_PROVIDER=auto              # auto | deepseek | openai | anthropic | gemini | ...
LLM_MODEL=                     # override the model for the active provider
LLM_MODEL_FALLBACKS=           # comma-separated fallback models
LLM_FALLBACK_PROVIDERS=        # opt-in cross-provider failover, e.g. openai,anthropic
LLM_TIMEOUT=120
LLM_MAX_TOKENS=8192
LLM_STRUCTURED_MODE=auto        # auto | json_schema | json_object | prompt
# LLM_PROVIDER=mock             # deterministic fake LLM, no network
```

The client uses each provider's native structured-output support where it
exists (`json_schema` or `json_object`) and falls back to a schema-in-prompt
mode otherwise. Results are always validated with Pydantic before the agents
use them.

### 2a. Run with Docker

```bash
docker compose up --build
```

| Module | URL |
|---|---|
| Mail — email agent | <http://localhost:8000> |
| Docs — document chat | <http://localhost:8001> |
| Lens — scrape & summarize | <http://localhost:8002> |

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

# Build the shared React UI once
cd frontend
npm install
npm run build
cd ..

# Seed demo data and check connectivity
python -m part1_email_agent.cli seed
python -m part1_email_agent.cli health
```

Start each service in its own terminal:

```bash
uvicorn part1_email_agent.web:app --port 8000   # Mail
uvicorn part3_doc_agent.web:app --port 8001     # Docs
uvicorn part2_scraper.web:app --port 8002       # Lens
```

## Tests

```bash
python -m pytest
```

Fully offline (mock LLM and hashing embedder), so no API key is needed.

## Project structure

```
core/                shared foundation; spa.py serves the React shell
core/providers/      provider adapters, auto-detection and model/provider failover
frontend/            one React/Vite app for Mail, Lens and Docs
part1_email_agent/   Mail: email agent + LangGraph
part2_scraper/       Lens: naive script + fixed pipeline
part3_doc_agent/     Docs: document chat agent + memory
knowledge_base/      fictional Nimbus Cloud sources and generated PDFs
data/                sample emails, seed script and runtime state
scripts/             threshold calibration, SMTP check, PDF/PPTX builders
tests/               offline test suite
```

> The demo knowledge base and sample emails use **Nimbus Cloud**, a fictional
> company created for this project. Any resemblance to a real company is
> coincidental.
