from __future__ import annotations

from core.llm import LLMClient
from core.logging_config import get_logger
from part3_doc_agent.models import CalculationPlan, RouterDecision

log = get_logger(__name__)

ROUTER_SYSTEM = """You are the routing component of a document-grounded assistant.

You do not answer the user. You decide what the assistant needs in order to
answer, and you record anything durable the user said about themselves.

You have exactly two tools available:

1. HANDBOOK SEARCH - looks up a fact in one internal document, the PointStar
   Cloud Subscription Plans & Pricing Handbook. Its sections are:
{toc}

2. CALCULATOR - evaluates one arithmetic expression. Nothing else.

Decide each flag independently. Many turns need neither tool, some need one,
some need both.

Set needs_document ONLY IF answering requires a fact from that handbook - a
price, a limit, a rate, a deadline, a threshold or a rule. Do NOT set it for
small talk, for questions about the user themselves, or for anything the
handbook plainly does not cover.

Set needs_calculation ONLY IF arithmetic has to be performed. Repeating a
number that already exists is not arithmetic. Comparing two stated numbers is
not arithmetic. Multiplying, dividing, totalling, applying a percentage or
prorating is arithmetic.

When you set needs_document, list one search query per distinct fact the answer
needs, in document_queries. If the answer needs a price AND a discount rate,
that is two queries, not one query mentioning both - they live in different
sections and a combined query finds neither well. Resolve every pronoun and
follow-up reference from the conversation, so each query stands on its own.

Set calculation_expression ONLY when every number needed is already present in
the user's message or in what you know about the user. If any number has to
come out of the handbook first, leave it null - the arithmetic gets written
after the lookup.

calculation_expression must contain digits, spaces, parentheses and the
operators + - * / % ** only. No words, no units, no currency symbols, no equals
sign. Write percentages as decimals: 15% off means multiplying by 0.85.

Record in memory_updates anything the user stated about themselves that stays
true later: their name, their company, their role, their plan, their seat
count, their country. Do not record their question, the answer, or anything you
inferred rather than being told. Return an empty list on turns where they
revealed nothing.

reasoning must be one short sentence, and must justify choosing no tool just as
explicitly as choosing one."""

ROUTER_EXAMPLES = """Examples:

User: "Hi, I'm Rega from the Jakarta office."
-> needs_document=false, needs_calculation=false, memory_updates=[name=Rega, office=Jakarta],
   reasoning="An introduction, not a question; nothing to look up, but the name and office are worth remembering."

User: "What's my name again?"
-> needs_document=false, needs_calculation=false, memory_updates=[],
   reasoning="The user is asking what they already told me, which is in memory, so no tool is needed."

User: "How much is the Business plan per seat?"
-> needs_document=true, document_queries=["Business plan price per seat per month"],
   needs_calculation=false, reasoning="A single price straight from the handbook, with no arithmetic on it."

User: "What's 15% of 4800?"
-> needs_document=false, needs_calculation=true, calculation_expression="0.15 * 4800",
   reasoning="Pure arithmetic with both numbers supplied, so only the calculator is needed."

User: "We need 14 Business seats for a year. What do we pay with the annual discount?"
-> needs_document=true,
   document_queries=["Business plan price per seat per month", "annual prepay discount percentage"],
   needs_calculation=true, calculation_expression=null,
   reasoning="The seat count is given but the rate and the discount are two separate handbook facts, so look both up and compute after."

User: "Thanks, that's really helpful!"
-> needs_document=false, needs_calculation=false, memory_updates=[],
   reasoning="Conversational acknowledgement with no question in it, so no tool is warranted."
"""

ROUTER_PROMPT = """{examples}

What you know about this user so far:
{memory_context}

Decide for this message:
<user_message>
{question}
</user_message>"""

def route(llm: LLMClient, question: str, memory_context: str, toc: str) -> RouterDecision:
    decision = llm.generate_structured(
        ROUTER_PROMPT.format(examples=ROUTER_EXAMPLES, memory_context=memory_context, question=question),
        RouterDecision,
        system=ROUTER_SYSTEM.format(toc=toc),
    )
    log.info(
        "routed",
        needs_document=decision.needs_document,
        needs_calculation=decision.needs_calculation,
        has_expression=bool(decision.calculation_expression),
        facts=len(decision.memory_updates),
        reasoning=decision.reasoning[:160],
    )
    return decision

PLANNER_SYSTEM = """You turn a question into one arithmetic expression, using numbers from the
supplied handbook context.

Return the expression only: digits, spaces, parentheses and + - * / % ** . No
words, no units, no currency symbols, no equals sign, no variable names.

Every number must come from the context or from the user's own message. If the
context does not contain a number you need, do not invent it and do not
substitute a plausible one - return the expression "0" and say which number was
missing in the explanation.

Percentages become multipliers: a 15 percent discount is "* 0.85", a 9 percent
tax is "* 1.09"."""

PLANNER_PROMPT = """Handbook context:
<context>
{context}
</context>

What you know about this user:
{memory_context}

<user_message>
{question}
</user_message>

Write the arithmetic that answers it."""

def plan_calculation(llm: LLMClient, question: str, context: str, memory_context: str) -> CalculationPlan:
    plan = llm.generate_structured(
        PLANNER_PROMPT.format(context=context, memory_context=memory_context, question=question),
        CalculationPlan,
        system=PLANNER_SYSTEM,
    )
    log.info("calculation_planned", expression=plan.expression[:120], explanation=plan.explanation[:160])
    return plan
