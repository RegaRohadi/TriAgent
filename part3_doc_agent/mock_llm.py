from __future__ import annotations

import re

from pydantic import BaseModel

from part3_doc_agent.models import CalculationPlan, GroundedAnswer, MemoryFact, RouterDecision

USER_MESSAGE = re.compile(r"<user_message>\s*(.*?)\s*</user_message>", re.S)
CONTEXT = re.compile(r"<context>\s*(.*?)\s*</context>", re.S)
CITATION = re.compile(r"\[([A-Z0-9\-]+ §[^\]]+)\]")
MEMORY_LINE = re.compile(r"^- ([a-z0-9_]+): (.+)$", re.M)
TOOL_LINE = re.compile(r"^- (\w+): (.+?) = (.+)$", re.M)
TOOL_FAILED = re.compile(r"^- (\w+): FAILED", re.M)

NAME_PATTERNS = (
    re.compile(r"\bmy name'?s?\s+is\s+([A-Z][\w'-]*)", re.I),
    re.compile(r"\bi\s+am\s+([A-Z][\w'-]*)", re.I),
    re.compile(r"\bi'm\s+([A-Z][\w'-]*)", re.I),
    re.compile(r"\bcall me\s+([A-Z][\w'-]*)", re.I),
)
COMPANY = re.compile(r"\b(?:from|at|work(?:ing)? (?:at|for))\s+(?:the\s+)?([A-Z][\w&.-]*(?:\s+[A-Z][\w&.-]*)?)")
SEATS = re.compile(r"\b(\d+)\s+(?:seats?|users?|licen[cs]es?)\b", re.I)
PLAN = re.compile(r"\b(starter|business|enterprise)\b", re.I)

DOC_TOPICS = (
    "price", "pricing", "cost", "charge", "fee", "rate", "seat", "plan", "starter", "business",
    "enterprise", "discount", "annual", "prepay", "billing", "cycle", "prorat", "storage", "quota",
    "overage", "gb", "tb", "sla", "uptime", "credit", "support", "response", "refund", "cancel",
    "tax", "gst", "sst", "ppn", "migration", "onboarding", "training", "handbook", "policy", "limit",
)
CALC_TRIGGERS = (
    "total", "calculate", "compute", "how much", "altogether", "times", "multiply", "sum",
    "per year", "for a year", "work out", "add up",
)
RECALL_TRIGGERS = ("my name", "who am i", "what did i", "do you remember", "what's my", "what is my")

GREETING = re.compile(r"^\s*(hi|hello|hey|good (?:morning|afternoon|evening)|halo|hai)\b", re.I)
THANKS = re.compile(r"\b(thanks|thank you|cheers|appreciate it|terima kasih)\b", re.I)

PERCENT_OF = re.compile(r"(\d+(?:\.\d+)?)\s*%\s*of\s*([\d,]+(?:\.\d+)?)", re.I)
BARE_ARITHMETIC = re.compile(r"\d[\d\s.,]*(?:[+\-*/]\s*[\d.,]+\s*)+")
NUMBER = re.compile(r"\d+(?:\.\d+)?")
DECIMAL = re.compile(r"\d+\.\d+")

class MockAgentLLM:

    name = "mock"

    def __init__(self) -> None:
        self.calls: list[str] = []

    def generate_structured(self, prompt: str, schema: type[BaseModel], *, system: str | None = None):
        self.calls.append(schema.__name__)
        question = self._extract(USER_MESSAGE, prompt)

        if schema is RouterDecision:
            return self._route(question)
        if schema is CalculationPlan:
            return self._plan(question, self._extract(CONTEXT, prompt))
        if schema is GroundedAnswer:
            return self._answer(question, prompt)
        raise NotImplementedError(f"MockAgentLLM has no rule for {schema.__name__}")

    @staticmethod
    def _extract(pattern: re.Pattern[str], prompt: str) -> str:
        match = pattern.search(prompt)
        return match.group(1).strip() if match else ""

    def _route(self, question: str) -> RouterDecision:
        lowered = question.lower()
        facts = self._extract_facts(question)

        if any(t in lowered for t in RECALL_TRIGGERS) and not any(t in lowered for t in DOC_TOPICS):
            return RouterDecision(
                needs_document=False,
                needs_calculation=False,
                memory_updates=facts,
                reasoning="The user is asking about something they already told me, so memory answers it.",
            )

        needs_document = any(topic in lowered for topic in DOC_TOPICS)
        expression = self._self_contained_expression(question)
        needs_calculation = bool(expression) or (
            any(trigger in lowered for trigger in CALC_TRIGGERS) and bool(NUMBER.search(question))
        )

        if not needs_document and not needs_calculation:
            return RouterDecision(
                needs_document=False,
                needs_calculation=False,
                memory_updates=facts,
                reasoning="Conversational turn with nothing to look up or compute.",
            )

        if needs_document:
            expression = None

        return RouterDecision(
            needs_document=needs_document,
            needs_calculation=needs_calculation,
            document_queries=[question] if needs_document else [],
            calculation_expression=expression,
            memory_updates=facts,
            reasoning=(
                f"Handbook lookup: {needs_document}; arithmetic: {needs_calculation} (mock keyword rules)."
            ),
        )

    @staticmethod
    def _extract_facts(question: str) -> list[MemoryFact]:
        facts: list[MemoryFact] = []
        for pattern in NAME_PATTERNS:
            match = pattern.search(question)
            if match:
                facts.append(MemoryFact(key="name", value=match.group(1)))
                break
        company = COMPANY.search(question)
        if company:
            facts.append(MemoryFact(key="company", value=company.group(1).strip()))
        seats = SEATS.search(question)
        if seats:
            facts.append(MemoryFact(key="seat_count", value=seats.group(1)))
        plan = PLAN.search(question)
        if plan:
            facts.append(MemoryFact(key="plan", value=plan.group(1).capitalize()))
        return facts

    @staticmethod
    def _self_contained_expression(question: str) -> str | None:
        percent = PERCENT_OF.search(question)
        if percent:
            return f"{float(percent.group(1)) / 100} * {percent.group(2).replace(',', '')}"
        bare = BARE_ARITHMETIC.search(question)
        if bare:
            return bare.group(0).strip()
        return None

    @staticmethod
    def _plan(question: str, context: str) -> CalculationPlan:
        quantity = NUMBER.search(question)
        rate = DECIMAL.search(context)
        if not quantity or not rate:
            return CalculationPlan(expression="0", explanation="Mock planner found no usable numbers.")
        months = 12 if re.search(r"year|annual|12 month", question, re.I) else 1
        return CalculationPlan(
            expression=f"{quantity.group(0)} * {rate.group(0)} * {months}",
            explanation=f"Mock planner: quantity {quantity.group(0)} from the question, rate {rate.group(0)} from the context.",
        )

    @staticmethod
    def _answer(question: str, prompt: str) -> GroundedAnswer:
        context = MockAgentLLM._extract(CONTEXT, prompt)
        citations = list(dict.fromkeys(CITATION.findall(context)))
        memory = dict(MEMORY_LINE.findall(prompt))
        tool_hits = TOOL_LINE.findall(prompt)
        name = memory.get("name")
        greeting = f"{name}, " if name else ""

        if TOOL_FAILED.search(prompt):
            return GroundedAnswer(
                answer="I could not complete that calculation, so I would rather not give you a number I am unsure of.",
                citations=citations,
                fully_answerable=False,
            )

        if tool_hits:
            _, expression, result = tool_hits[0]
            return GroundedAnswer(
                answer=f"{greeting}that works out to {result} ({expression}).".capitalize(),
                citations=citations[:2],
                fully_answerable=True,
            )

        lowered = question.lower()
        if any(t in lowered for t in RECALL_TRIGGERS):
            if "name" in lowered:
                if name:
                    return GroundedAnswer(answer=f"You told me your name is {name}.", citations=[], fully_answerable=True)
                return GroundedAnswer(answer="You have not told me your name yet.", citations=[], fully_answerable=False)
            if memory:
                facts = ", ".join(f"{k.replace('_', ' ')} is {v}" for k, v in memory.items())
                return GroundedAnswer(answer=f"Here is what you have told me: {facts}.", citations=[], fully_answerable=True)
            return GroundedAnswer(answer="You have not told me anything about yourself yet.", citations=[], fully_answerable=False)

        if GREETING.search(question):
            return GroundedAnswer(
                answer=f"Good to meet you{', ' + name if name else ''}. Ask me anything about the plans and pricing handbook.",
                citations=[],
                fully_answerable=True,
            )
        if THANKS.search(question):
            return GroundedAnswer(answer="Happy to help. Anything else?", citations=[], fully_answerable=True)

        if not context or context.startswith("NO RELEVANT CONTEXT"):
            return GroundedAnswer(
                answer="The handbook does not cover that, so I cannot answer it from this document.",
                citations=[],
                fully_answerable=False,
            )

        excerpt = re.sub(r"\[[^\]]+\]\s*", "", context).strip()
        if citations:
            heading = citations[0].split("§", 1)[-1].strip()
            if excerpt.startswith(heading):
                excerpt = excerpt[len(heading) :].strip()
        sentence = re.split(r"(?<=[.!?])\s+", excerpt)[0][:400]
        return GroundedAnswer(answer=f"{greeting}{sentence}".strip(), citations=citations[:1], fully_answerable=True)
