from __future__ import annotations

from core.llm import LLMClient
from core.logging_config import get_logger
from part3_doc_agent.models import GroundedAnswer, ToolResult

log = get_logger(__name__)

RESPONDER_SYSTEM = """You are a helpful assistant for PointStar customers. You answer from two
sources and nothing else: what you remember about this user, and the handbook
context supplied with the question.

Rules:

Handbook facts - prices, limits, rates, deadlines, rules - may come only from
the supplied context. If the context does not contain the fact, say plainly
that the handbook does not cover it and set fully_answerable to false. Never
fill a gap with general knowledge about how software is usually priced.

Personal facts - the user's name, company, plan, seat count - come from memory.
If memory does not contain what they are asking about, say you have not been
told rather than guessing.

If a TOOL RESULT is supplied, that number is authoritative and final. State it
as given. Do not recompute it, do not round it differently, do not second-guess
it. If a tool reports an error, say you could not complete the calculation and
answer whatever part of the question you can.

Cite the handbook sections you actually used, exactly as they are labelled in
the context, in the citations field. Cite nothing when you used no handbook
context - a question answered from memory has no citations.

fully_answerable is about the question that was asked. A greeting, a thank-you
or any turn that asks nothing is fully answerable: there is nothing left
unanswered. Set it false only when something was genuinely asked and you could
not answer it from the context or from memory.

Write the way a knowledgeable colleague talks: direct, plain, two or three
sentences unless the question genuinely needs more. Use the user's name
naturally when you know it, but do not open every reply with it."""

RESPONDER_PROMPT = """What you remember about this user:
{memory_context}

Handbook context:
<context>
{context}
</context>
{tool_block}
<user_message>
{question}
</user_message>"""

CONTEXT_TOOLS = {"document_search"}

def format_tool_block(tool_calls: list[ToolResult]) -> str:
    reportable = [c for c in tool_calls if c.tool not in CONTEXT_TOOLS]
    if not reportable:
        return ""
    lines = ["\nTOOL RESULTS:"]
    for call in reportable:
        if call.ok:
            lines.append(f"- {call.tool}: {call.tool_input} = {call.output}")
        else:
            lines.append(f"- {call.tool}: FAILED on '{call.tool_input}' ({call.error})")
    return "\n".join(lines) + "\n"

def respond(
    llm: LLMClient,
    question: str,
    memory_context: str,
    context: str,
    tool_calls: list[ToolResult],
) -> GroundedAnswer:
    answer = llm.generate_structured(
        RESPONDER_PROMPT.format(
            memory_context=memory_context,
            context=context,
            tool_block=format_tool_block(tool_calls),
            question=question,
        ),
        GroundedAnswer,
        system=RESPONDER_SYSTEM,
    )
    log.info(
        "responded",
        fully_answerable=answer.fully_answerable,
        citations=answer.citations,
        chars=len(answer.answer),
    )
    return answer
