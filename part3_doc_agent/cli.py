from __future__ import annotations

import argparse

from core.config import settings
from core.logging_config import configure_logging
from part3_doc_agent.graph import DocumentAgent
from part3_doc_agent.memory import ConversationMemory
from part3_doc_agent.models import AgentState

RULE = "=" * 78

DEMO_SCRIPT = [
    "Hi, I'm Rega and I look after IT for a design studio in Jakarta.",
    "How much is the Business plan per seat?",
    "What's 15% of 4800?",
    "We need 14 Business seats for a year. What would we pay with the annual discount?",
    "What service credit would we get for 99.2% uptime?",
    "Remind me, what's my name?",
    "Who won the World Cup in 2022?",
]

def print_turn(state: AgentState, verbose: bool = False) -> None:
    answer = state.answer
    print(f"\n{answer.answer if answer else '(no answer)'}")

    tools = ", ".join(state.tools_used) if state.tool_calls else "none"
    footer = f"  [tools: {tools}"
    if answer and answer.citations:
        footer += f" | source: {'; '.join(answer.citations)}"
    if answer and not answer.fully_answerable:
        footer += " | not fully covered by the handbook"
    print(footer + "]")

    if verbose:
        if state.decision:
            print(f"  routing  : {state.decision.reasoning}")
            for query in state.decision.document_queries:
                print(f"  query    : {query}")
        if state.calculation:
            print(f"  arithmetic: {state.calculation.expression}  ({state.calculation.explanation})")
        for call in state.tool_calls:
            status = call.output if call.ok else f"FAILED: {call.error}"
            print(f"  tool     : {call.tool}({call.tool_input}) -> {status}")
        path = " -> ".join(f"{e.node}:{e.outcome}" for e in state.trace)
        print(f"  path     : {path}")

def _agent_and_memory(args: argparse.Namespace) -> tuple[DocumentAgent, ConversationMemory]:
    agent = DocumentAgent()
    memory = ConversationMemory.load(args.session)
    if getattr(args, "reset", False):
        memory.clear()
        memory.save()
    return agent, memory

def cmd_demo(args: argparse.Namespace) -> int:
    agent = DocumentAgent()
    memory = ConversationMemory.load("demo")
    memory.clear()

    print(f"\n{RULE}\nDocument-grounded agent — scripted walkthrough")
    print(f"document : {settings.chat_document_path.name}")
    print(f"llm      : {agent.llm.name}")
    print(f"session  : {memory.session_id}\n{RULE}")

    summary: list[tuple[str, str]] = []
    for question in DEMO_SCRIPT:
        print(f"\n> {question}")
        state = agent.chat(question, memory)
        print_turn(state, verbose=args.verbose)
        summary.append((question, ", ".join(state.tools_used) if state.tool_calls else "none"))

    print(f"\n{RULE}\nTool decisions — the agent reached for a tool only where one was needed\n{RULE}")
    width = max(len(q) for q, _ in summary)
    for question, tools in summary:
        print(f"  {question:<{width}}  {tools}")

    reloaded = ConversationMemory.load(memory.session_id)
    print(f"\n{RULE}\nMemory persisted to {reloaded.path}")
    for key, value in reloaded.profile.items():
        print(f"  {key:<12} {value}")
    print(RULE)
    return 0

def cmd_ask(args: argparse.Namespace) -> int:
    agent, memory = _agent_and_memory(args)
    print_turn(agent.chat(args.question, memory), verbose=args.verbose)
    return 0

HELP = """
  /memory   show what the agent remembers about you
  /forget   clear this session's memory
  /verbose  toggle routing details
  /help     this list
  /exit     leave
"""

def cmd_chat(args: argparse.Namespace) -> int:
    agent, memory = _agent_and_memory(args)
    verbose = args.verbose

    print(f"\n{RULE}")
    print(f"Ask me about {settings.chat_document_path.name}. I remember what you tell me.")
    print(f"session: {memory.session_id}   llm: {agent.llm.name}   /help for commands")
    if memory.profile:
        print(f"picking up where we left off: {', '.join(f'{k}={v}' for k, v in memory.profile.items())}")
    print(RULE)

    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            return 0

        if not question:
            continue
        if question in {"/exit", "/quit"}:
            print("Bye.")
            return 0
        if question == "/help":
            print(HELP)
            continue
        if question == "/verbose":
            verbose = not verbose
            print(f"  routing details {'on' if verbose else 'off'}")
            continue
        if question == "/memory":
            if memory.profile:
                for key, value in memory.profile.items():
                    print(f"  {key:<12} {value}")
            else:
                print("  I have not been told anything about you yet.")
            print(f"  ({len(memory.turns)} recent turns buffered, saved at {memory.path})")
            continue
        if question == "/forget":
            memory.clear()
            memory.save()
            print("  Memory cleared.")
            continue

        print_turn(agent.chat(question, memory), verbose=verbose)

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="part3_doc_agent", description="Conversational agent grounded in a single document"
    )
    parser.add_argument("--log-json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_demo = sub.add_parser("demo", help="scripted walkthrough showing when tools are and are not used")
    p_demo.add_argument("--verbose", action="store_true", help="show routing reasoning and the graph path")
    p_demo.set_defaults(func=cmd_demo)

    p_chat = sub.add_parser("chat", help="interactive conversation with memory")
    p_chat.add_argument("--session", default="default", help="conversation to continue (default: default)")
    p_chat.add_argument("--reset", action="store_true", help="start this session from an empty memory")
    p_chat.add_argument("--verbose", action="store_true")
    p_chat.set_defaults(func=cmd_chat)

    p_ask = sub.add_parser("ask", help="ask a single question")
    p_ask.add_argument("question")
    p_ask.add_argument("--session", default="default")
    p_ask.add_argument("--reset", action="store_true")
    p_ask.add_argument("--verbose", action="store_true")
    p_ask.set_defaults(func=cmd_ask)

    args = parser.parse_args(argv)
    quiet = args.quiet or (args.command == "demo" and not args.verbose)
    configure_logging(json_output=args.log_json, level="WARNING" if quiet else "INFO")
    return args.func(args)

if __name__ == "__main__":
    raise SystemExit(main())
