# Speaker Notes - TriAgent

Companion notes for `presentation/TriAgent_Presentation.pptx`.
Each slide has: a 30-60s script, the point to remember, one likely follow-up
question, and a concise answer. Appendices A-E follow at the end.

> Anything not verifiable from the repository is marked `[NEEDS MY INPUT]`.

## Slide 1 - TriAgent

SCHEDULE (30-60s): Introduce yourself and the assessment in one line. Say the subtitle out loud: 'The core principle is that deterministic code decides; the LLM only extracts and writes.' Name the three subsystems and the shared core.

REMEMBER: This is an engineering-decision walkthrough, not a feature demo.

FOLLOW-UP Q: What does 'deterministic code decides' actually mean?
A: Money, security and escalation rules are enforced in Python (thresholds, regex, citation checks). The model is used for understanding and language, never as the authority on policy.

## Slide 2 - Problem & Objective

SCHEDULE (30-60s): Set up the problem in two buckets. Business: answer email safely and escalate exceptions. Engineering: ground answers, survive long content, keep control flow testable and observable. Then deliver the punchline about why one prompt is not enough.

REMEMBER: The hard part is not generating text; it is making correct, safe decisions under uncertainty.

FOLLOW-UP Q: Why can't you just prompt a big model with all the policy documents?
A: Context windows overflow, the model can still hallucinate amounts, and there is no way to guarantee or audit a numeric policy rule. So we retrieve only relevant chunks and enforce limits in code.

## Slide 3 - Solution Overview

SCHEDULE (30-60s): Walk left to right. Everything sits on the shared core. Part 1 is an agent that can hand off to a human; Part 2 is deliberately a plain pipeline; Part 3 is a grounded chat agent. Close with the common end-to-end shape.

REMEMBER: One codebase, one config, three different problem shapes — and I matched the architecture to each shape.

FOLLOW-UP Q: Why is Part 2 a pipeline if the other two are agents?
A: Summarizing a page has a fixed sequence with no branching decisions; adding agentic routing would add cost and failure modes with no benefit. Use an agent only when decisions actually branch.

## Slide 4 - Architecture

SCHEDULE (45-60s): Trace one arrow: UI/API calls the shared core, which builds a model client and a knowledge base. Part 1 can stop at any node and emit a human ticket (human-in-the-loop). Point at the amber bar: these are the places where Python, not the model, makes the decision.

REMEMBER: The architecture separates 'what the model perceives' from 'what the system is allowed to do'.

FOLLOW-UP Q: Where exactly is the human-in-the-loop?
A: In Part 1, any failed or uncertain check routes to route_human, which stores a ticket and sends an acknowledgement. A human can reply from the web UI, guarded so an already-resolved ticket cannot be answered twice.

## Slide 5 - Agentic Workflow / State Machine

SCHEDULE (45-60s): Walk the eight nodes once, then point at the redraft loop and the amber exit. Emphasize the three properties that make it agentic: branching, self-verification, and termination/escalation.

REMEMBER: 'Agentic' here means controlled branching with an escape hatch — not unbounded autonomy.

FOLLOW-UP Q: Isn't a verify-then-retry loop dangerous — it could loop forever?
A: It is bounded: MAX_REDRAFT_ATTEMPTS defaults to 1, then the email escalates. The retry also receives the exact verifier feedback.

## Slide 6 - Critical Guardrails & Safety

SCHEDULE (45-60s): This is the safety story. Precheck runs before any model call and combines fast regex with semantic similarity, with a benign margin so normal requests do not trigger it. The refund guard is the clearest example: the model only extracts facts, Python compares them to limits.

REMEMBER: Safety is layered, and the last layer is always escalation.

FOLLOW-UP Q: Why combine regex and embeddings instead of one?
A: Regex is precise and cheap but brittle to paraphrases; embeddings catch paraphrases but can false-positive. Using both, with the semantic layer requiring a margin over benign anchors, raises recall while keeping false positives manageable — and false positives only cost a human review, not a wrong reply.

## Slide 7 - Knowledge Retrieval / Grounded Responses

SCHEDULE (45-60s): Explain the four-step flow and the two independent checks. Stress the escape path: if the knowledge base does not clear the floor, the agent escalates rather than answering.

REMEMBER: A confident-sounding answer is not the goal; a grounded, cited answer is.

FOLLOW-UP Q: What if two documents conflict?
A: Retrieval returns both, but the policy layer prefers the refund policy for refund questions, and anything NetSuite-related or above threshold goes to a human. The system never silently chooses between conflicting policy clauses.

## Slide 8 - Technical Implementation — Scraper (Part 2)

SCHEDULE (45-60s): Show the naive failure first, then the four-step fix. The length guardrail is the interesting bit: it measures, asks the model to rewrite while quoting the actual count, and only truncates as a last resort. Numbers shown are from a mock-model demo run, so treat them as plumbing evidence, not model quality.

REMEMBER: The bottleneck was input size and noise, not model capability — so the fix is upstream of the model.

FOLLOW-UP Q: Why not just use a bigger context window?
A: Bigger windows are costly and still degrade with noise. Extraction plus chunking is cheaper, faster, and keeps the important facts. Map-reduce also gives a bounded, predictable cost per page.

## Slide 9 - Memory & Tool Calling (Part 3)

SCHEDULE (45-60s): Separate two ideas: memory (what we know about the user) and tools (what the agent can do). The router's job is the decision; the graph's job is execution. Point out the calculator uses an AST whitelist, not eval.

REMEMBER: Over-calling tools is a real failure mode — it adds latency and can inject unnecessary context.

FOLLOW-UP Q: How does the agent know not to search the handbook for 'what's my name'?
A: The router is instructed and few-shot-prompted to set needs_document=false for memory and small-talk turns; that decision is explicit and shown in the trace, and demo runs confirm no tool is called.

## Slide 10 - Reliability & Failure Handling

SCHEDULE (45-60s): Cover the table in three groups: model/network failures (failover, retry), logic/uncertainty failures (fail closed, redraft then escalate), and delivery failures (idempotent claim, dead-letter).

REMEMBER: There is no silent failure mode — every failure is either retried, escalated, or surfaced as an explicit message.

FOLLOW-UP Q: What if the same email is delivered twice at the same moment?
A: claim_message runs inside BEGIN IMMEDIATE and records a message_attempts row, so only one worker wins the claim; the other skips. A TTL handles stale in-progress claims, and repeated failures become dead-letters for inspection.

## Slide 11 - Testing & Evaluation

SCHEDULE (45-60s): Explain the strategy: a mock LLM and a hashing embedder make the whole suite offline and deterministic, so CI runs without an API key. We assert on control flow, guardrails and tool decisions. Then mention the in-app metrics for ongoing evaluation. Counts are from static analysis of the test files.

REMEMBER: We do not try to unit-test the model's wording; we test that the system reacts correctly to whatever the model returns.

FOLLOW-UP Q: How do you test something non-deterministic?
A: You isolate it. The LLM sits behind a small interface; tests inject a mock that returns fixed or adversarial outputs, so we can assert escalation, redraft and error paths precisely. Real-model quality is a separate, offline evaluation.

## Slide 12 - Trade-offs & Design Decisions

SCHEDULE (60s): Do not read the table. Pick two rows and go deep — the rules-vs-LLM split and the human-in-the-loop decision. For each, state the decision, the reason, and the downside honestly.

REMEMBER: A good engineer names the downside of their own choice; that is what makes the design credible.

FOLLOW-UP Q: Which trade-off was hardest?
A: Drawing the line on what the model may decide. Too strict and it is just a rules engine; too loose and money/security outcomes become non-deterministic. I chose to keep extraction and language in the model, and all consequential decisions in code.

## Slide 13 - Observability / AgentOps

SCHEDULE (45-60s): Explain that the same structure that makes it testable makes it debuggable. Given a wrong answer, we replay the trace and localise the fault: retrieval, classification, or generation. Be explicit that cost/token tracking is a gap.

REMEMBER: Observability is designed in from the start via per-node traces, not bolted on afterwards.

FOLLOW-UP Q: How would you evaluate the agent after deployment?
A: Track the auto-resolution rate against escalation reasons, watch latency percentiles and node error rates, and sample escalated tickets to check whether they should have been automated. Threshold calibration uses the same signal.

## Slide 14 - Limitations & Future Improvements

SCHEDULE (45-60s): Be candid and specific. Distinguish what is implemented from what is proposed. Do not say 'improve accuracy' — name the mechanism: calibration, re-ranking, queueing, cost metrics.

REMEMBER: Naming real limitations is a strength, not a weakness; it signals production awareness.

FOLLOW-UP Q: What is the single most important next step?
A: A golden-set evaluation against the real model, because it turns every threshold and prompt choice from a guess into a measured decision — and it will drive the other improvements.

## Slide 15 - Reviewer Q&A Preparation

SCHEDULE (30-45s): Do not read this slide. Use it as a map: say 'I prepared answers to the likely hard questions' and then offer to go deeper on any row. The full set of 20 questions with answers is in the speaker notes appendix.

REMEMBER: Confidence comes from having a concrete, honest answer for each row — not from avoiding the question.

FOLLOW-UP Q: Which of these is your weakest answer?
A: Scaling to thousands of emails, because the current storage and poller are single-node. I have a concrete plan (queue + Postgres + horizontal workers) but I have not implemented or load-tested it yet.

## Slide 16 - Key Takeaways

SCHEDULE (30-45s): Close on the four principles. Deliver the closing line slowly. Then invite the reviewer to pick any decision to drill into.

REMEMBER: The throughline is trust: every design choice exists to make the system's behaviour predictable and safe.

FOLLOW-UP Q: What would you change if you had more time?
A: Run a golden-set evaluation against the real model to calibrate thresholds, then add retrieval re-ranking and token/cost metrics — the improvements that turn tuning from guesswork into measurement.

## Slide 17 - Appendix — Test Coverage Matrix

Reference slide. Use only if the reviewer asks for test detail. Counts come from a static count of test functions.

## Slide 18 - Appendix — Configurable Behaviour (defaults)

Reference slide. All values come from core/config.py defaults and .env.example.

## Slide 19 - Appendix — Claims to Verify Before Presenting

Private checklist. Resolve every item and delete this slide before the real interview.

---

# Appendix A - 5-Minute Presentation Version

Use this when the reviewer says "walk me through it in five minutes". Skip the
tables; keep the throughline. Times are cumulative.

| Time | Slide | What to say |
|---|---|---|
| 0:00 | 1 | "Three AI systems on one shared core. Core principle: deterministic code decides; the LLM extracts and writes." |
| 0:20 | 2 | Business need: answer support email safely and escalate exceptions. Engineering need: grounding, context limits, testability, idempotency. |
| 0:50 | 3-4 | Show the three parts on the shared core; point at the amber "deterministic control points" bar. |
| 1:30 | 5-6 | Part 1 state machine: eight nodes, bounded redraft, escalation. Safety layers: triage -> precheck -> classify -> retrieve -> refund guard -> verify. |
| 2:40 | 7 | Grounding: retrieve -> constrain -> cite -> verify -> escalate if unsure. |
| 3:10 | 8 | Scraper: the bottleneck was input size/noise, not the model; fix is extraction + chunking + map-reduce + length guardrail. |
| 3:45 | 9 | Part 3: memory vs tools; the router decides, code executes; tools only when needed. |
| 4:10 | 10-11 | Reliability table in three groups; 267 offline tests make non-determinism testable. |
| 4:35 | 12 | Name one trade-off deeply: rules for money/security, LLM for language. |
| 4:50 | 14/16 | One limitation (mock vs real model) and close on trust. |

# Appendix B - 10-Minute Presentation Version

| Time | Slides | Focus |
|---|---|---|
| 0:00-0:45 | 1-2 | Title, principle, problem split into business vs engineering, why one LLM call fails. |
| 0:45-2:15 | 3-5 | Architecture tour and both state machines. Emphasize Part 2 is deliberately a pipeline. Explain branching, self-verification, termination. |
| 2:15-4:00 | 6-7 | Guardrails layer by layer; grounding and the two independent checks (citation + fact-check). Mention the false-positive demo case and why over-escalation is the safe failure. |
| 4:00-5:30 | 8-9 | Scraper bottleneck and fix with the observed metrics (mock); memory vs tool calling and the AST calculator. |
| 5:30-7:00 | 10-11 | Failure handling table in three groups; testing strategy (mock LLM + hashing embedder) and in-app metrics. |
| 7:00-8:15 | 12-13 | Trade-offs (pick two deep) and observability: how to debug a wrong answer via trace_id. |
| 8:15-9:15 | 14 | Limitations honestly, each paired with a concrete next step. |
| 9:15-10:00 | 15-16 | Offer the Q&A map; close on the four principles. |

---

# Appendix C - 20 Most Likely Reviewer Questions

1. **Why is this an agent and not just an LLM pipeline?**
   It branches on state, selects tools, self-checks with a bounded retry, and has explicit termination and escalation. A pipeline is linear; here the next step depends on confidence, signals and verification.

2. **Why LangGraph instead of a simpler implementation?**
   It makes states, conditional edges and the accumulated trace explicit and testable. Where the task is linear (the scraper), I deliberately used plain code instead.

3. **Why not let the LLM decide whether an email is critical?**
   Criticality has safety consequences and must be deterministic and auditable. Regex plus embedding anchors plus code thresholds are testable; LLM confidence is not reliable enough for that decision.

4. **How do you prevent hallucinations?**
   Ground every claim in retrieved context, require citations, verify the cited IDs exist, run an independent fact-check, and escalate when the draft is not fully answerable. The refund rules are enforced in Python, not by the model.

5. **What happens if the model returns an invalid classification?**
   Output is schema-validated by Pydantic. If top confidence is below the threshold, we escalate. If a model call fails outright, the node wrapper fails closed to a human ticket.

6. **What if the knowledge base has no answer?**
   Nothing clears the minimum-score floor, so the retrieve step escalates without drafting. If context is partially relevant, the draft marks itself not fully answerable and escalates.

7. **How do you handle conflicting information?**
   Policy decides precedence (for example, the refund policy governs refund questions), and anything NetSuite-related or above the refund threshold always goes to a human. The system never silently picks a side.

8. **How do you test non-deterministic LLM behaviour?**
   The LLM sits behind a small interface with a deterministic mock and a hashing embedder, so tests run offline and assert control flow, guardrails and tool decisions rather than prose. Real-model quality is a separate evaluation.

9. **How do you control latency and cost?**
   Few model calls per item, temperature 0, bounded retries, a bounded number of chunks (top-k), and map-reduce only when content exceeds the window. Per-call token/cost accounting is a proposed next step.

10. **How would this scale to thousands of emails?**
    Processing is already idempotent via a claim table and dead-letter queue, so workers can run concurrently. To scale, move from SQLite to Postgres and from the in-process poller to a queue with horizontal workers.

11. **What happens if a tool fails?**
    Tools return a structured `ToolResult(ok=false)` instead of raising; the responder states it could not compute and answers whatever part it can.

12. **Why is human-in-the-loop necessary?**
    Money, security and policy exceptions should not be auto-decided by a probabilistic model. Escalation also gives us labelled data for improving thresholds.

13. **How would you improve this architecture for production?**
    Centralise storage (Postgres), move ingestion to a queue, add token/cost metrics and budget alerts, encrypt sessions, pin resolved IPs, calibrate thresholds on a golden set, and add retrieval re-ranking.

14. **What was the hardest engineering trade-off?**
    Deciding what the model is allowed to decide. Too strict and it becomes a rules engine; too loose and consequential outcomes become non-deterministic. I kept extraction and language in the model and all consequential decisions in code.

15. **What would you change if you had more time?**
    A golden-set evaluation against the real model, because it converts every threshold and prompt choice from a guess into a measurement, then re-ranking and cost metrics.

16. **Why not use a vector database?**
    The knowledge base is small (five documents). In-memory vectors with a cached index are simpler and fast enough; a vector DB would add operational overhead without benefit at this scale.

17. **How do you avoid answering the same email twice?**
    A message claim inside an immediate transaction records the attempt; only one worker wins, and the TTL handles stale claims. Successful messages are recorded and never reprocessed.

18. **Is it production-ready?**
    No. It is a working prototype with strong safety and testing patterns, but it runs on mocks for tests, uses SQLite and an in-process poller, and its thresholds are not yet calibrated on real traffic.

19. **What did you learn?**
    That the valuable engineering is in the boundaries: what the model may decide, how the system fails, and how you prove it behaves correctly.

20. **What is the single most important design decision?**
    Separating perception from authority. The model perceives and writes; deterministic code owns every decision with money, security or irreversibility attached.

---

# Appendix D - Technical Details You Must Understand Before Presenting

- **LangGraph `StateGraph`**: nodes are functions, edges are conditional; state is a typed object accumulated across nodes. Be able to explain `add_conditional_edges` and why `_after_verify` can loop back.
- **Pydantic schema in the prompt**: the provider adapter sends the Pydantic JSON Schema and validates the response with `model_validate_json`; invalid output is retried or surfaced as a node error.
- **Embeddings and cosine similarity**: vectors are normalised, similarity is a dot product; the precheck uses a contrastive margin against benign anchors to reduce false positives.
- **Chunking**: section-aware chunks in the RAG layer; token-estimated chunks with overlap in the scraper. Know why overlap matters.
- **Map-reduce summarization**: map summarizes each chunk, reduce merges; a loop shrinks until it fits; a length guardrail then enforces the word budget.
- **Idempotency**: `claim_message` uses `BEGIN IMMEDIATE` plus an attempts table, with a TTL and dead-letter state.
- **Fail-closed node wrapper**: `_run_node` catches every exception and converts it into a human escalation with the error recorded in the trace.
- **Model/provider failover**: errors are classified as quota / balance / auth / unavailable / transient; quota triggers a cooldown, unavailable blocks the model, transient retries with backoff, and an optional cross-provider chain tries the next configured provider.
- **AST calculator**: `ast.parse(mode="eval")` with a whitelist of operators, plus guards for division by zero and huge exponents. Never `eval`.
- **SSRF guard**: resolve the hostname and reject non-global addresses before fetching.
- **structlog**: structured logs with a bound `trace_id`; optional JSON output for aggregation.
- **Metrics**: auto-resolution rate, route reasons, latency p50/p95 per node, node errors, redrafts, dead-letters.

---

# Appendix E - Claims That Require Verification Before Presenting

- [ ] Did the three parts ever run end-to-end against a live provider (DeepSeek/OpenAI/Anthropic/Gemini), or only in mock mode?
- [ ] Confirm the configured provider model names exist and are reachable in your environment.
- [ ] Run `python -m pytest` and record the actual pass/fail count (this document only counts test functions: 237).
- [ ] Demo metrics (latency, cosine scores, byte counts) were produced in mock mode - label them as plumbing evidence, not model quality.
- [ ] Was camoufox actually installed and its fallback exercised, or left disabled?
- [ ] Do the IMAP/SMTP credentials point to a real mailbox used for a live demo?
- [ ] Confirm your full name, role and the official assessment title for the title slide.
- [ ] Confirm the exact test counts per file if you quote them individually.
