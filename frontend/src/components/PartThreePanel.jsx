import { useCallback, useEffect, useRef, useState } from "react";
import { RiChat3Line, RiDeleteBin6Line, RiRefreshLine, RiSendPlaneLine } from "@remixicon/react";
import { api3 } from "../api3.js";
import { apiBase } from "../backend.js";
import { Button } from "@/components/base/buttons/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { Chip } from "@/components/base/badges/chip";
import { InputBase, TextField } from "@/components/base/input/input";
import { Spinner } from "@/components/base/spinner/spinner";

const SESSION_KEY = "triagent_session_id";

const SUGGESTIONS = [
  "Hi, I'm Rega and I run IT for a design studio in Jakarta.",
  "How much is the Business plan per seat?",
  "What's 15% of 4800?",
  "We need 14 Business seats for a year — what would we pay with the annual discount?",
  "What service credit applies at 99.2% uptime?",
  "Remind me, what's my name?",
  "Who won the World Cup in 2022?",
];

function sessionId() {
  const fromUrl = new URLSearchParams(location.search).get("session");
  if (fromUrl) {
    const clean = fromUrl.trim().slice(0, 64);
    if (clean) {
      localStorage.setItem(SESSION_KEY, clean);
      return clean;
    }
  }
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id = "web-" + Math.random().toString(36).slice(2, 9);
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

function Bubble({ message }) {
  const user = message.role === "user";
  return (
    <div className={user ? "flex max-w-[82%] flex-col items-end gap-1.5 self-end" : "flex max-w-[82%] flex-col gap-1.5 self-start"}>
      <div
        className={[
          "whitespace-pre-wrap px-3.5 py-2.5 text-body-regular",
          user
            ? "rounded-2xl rounded-br-md bg-accent-600 text-text-white"
            : "rounded-2xl rounded-bl-md bg-background-secondary-default text-text-primary",
          message.pending ? "italic text-text-secondary" : "",
        ].join(" ")}
      >
        {message.content}
      </div>
      {message.details ? <AnswerMeta data={message.details} /> : null}
    </div>
  );
}

function DetailRow({ term, value }) {
  if (!value) return null;
  return (
    <>
      <dt className="font-semibold text-text-secondary">{term}</dt>
      <dd className="break-words font-mono text-caption-1-regular">{value}</dd>
    </>
  );
}

function AnswerMeta({ data }) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex flex-wrap items-center gap-1.5">
        {data.tools_used.length === 0 ? (
          <Chip color="lime" variant="caption">no tools needed</Chip>
        ) : (
          data.tools_used.map((tool) => (
            <Chip key={tool} color="blue" variant="caption">{tool}</Chip>
          ))
        )}
        {!data.fully_answerable ? (
          <Chip color="yellow" variant="caption">not fully in the handbook</Chip>
        ) : null}
        {data.citations.map((citation) => (
          <code key={citation} className="font-mono text-caption-1-regular text-text-secondary">
            {citation}
          </code>
        ))}
      </div>

      <details className="text-caption-1-regular text-text-secondary">
        <summary className="cursor-pointer font-medium text-accent-600">why this happened</summary>
        <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
          <DetailRow term="routing" value={data.routing_reason} />
          <DetailRow term="queries" value={data.queries?.join("  |  ")} />
          <DetailRow
            term="arithmetic"
            value={
              data.calculation
                ? `${data.calculation.expression}   — ${data.calculation.explanation}`
                : null
            }
          />
          {data.tool_calls.map((call) => (
            <DetailRow
              key={`${call.tool}-${call.tool_input}`}
              term={call.tool}
              value={`${call.tool_input} -> ${call.ok ? call.output : "FAILED: " + call.error}`}
            />
          ))}
          <DetailRow
            term="retrieved"
            value={data.retrieved.map((item) => `${item.citation} (${item.score})`).join("\n")}
          />
          <DetailRow term="path" value={data.trace.map((event) => `${event.node}:${event.outcome}`).join(" -> ")} />
        </dl>
      </details>
    </div>
  );
}

function MemoryCard({ memory, onForget, busy }) {
  const keys = Object.keys(memory || {});
  return (
    <Card>
      <CardHeader>
        <CardTitle>What I remember</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {keys.length === 0 ? (
          <p className="text-body-2-regular text-text-secondary">
            You have not told me anything about yourself yet.
          </p>
        ) : (
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-body-2-regular">
            {keys.map((key) => (
              <div key={key} className="contents">
                <dt className="text-text-secondary">{key.replace(/_/g, " ")}</dt>
                <dd className="font-semibold text-text-primary">{memory[key]}</dd>
              </div>
            ))}
          </dl>
        )}
        <Button
          variant="secondary"
          size="small"
          leadingIcon={RiDeleteBin6Line}
          onClick={onForget}
          disabled={busy || keys.length === 0}
          className="self-start"
        >
          Forget everything
        </Button>
      </CardContent>
    </Card>
  );
}

function SourceCard({ health }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Source document</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        <p className="text-caption-1-regular text-text-secondary">{health?.document || "—"}</p>
        <ul className="list-disc space-y-1 pl-4 text-caption-1-regular text-text-secondary">
          {(health?.sections || []).map((section) => (
            <li key={section}>{section.replace(/^-\s*/, "")}</li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}

function UnavailableCard({ onRetry }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Docs is not running</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col items-start gap-3">
        <p>
          Nothing answered at <code className="font-mono">{apiBase("part3")}</code>. Start it with:
        </p>
        <pre className="w-full rounded-xl bg-background-secondary-default p-3 font-mono text-body-2-regular">
          docker compose up -d chat
        </pre>
        <p className="text-caption-1-regular text-text-secondary">
          Without Docker: <code className="font-mono">uvicorn part3_doc_agent.web:app --port 8001</code>
        </p>
        <Button variant="secondary" size="small" leadingIcon={RiRefreshLine} onClick={onRetry}>
          Try again
        </Button>
      </CardContent>
    </Card>
  );
}

export function PartThreePanel({ active }) {
  const [id] = useState(sessionId);
  const [health, setHealth] = useState({ status: "loading", data: null });
  const [messages, setMessages] = useState([]);
  const [memory, setMemory] = useState({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  const load = useCallback(() => {
    setHealth({ status: "loading", data: null });
    api3
      .health()
      .then((data) => setHealth({ status: "up", data }))
      .catch(() => setHealth({ status: "down", data: null }));

    api3
      .session(id)
      .then((session) => {
        setMemory(session.memory || {});
        setMessages(
          (session.turns || []).map((turn) => ({ role: turn.role, content: turn.content })),
        );
      })
      .catch(() => {});
  }, [id]);

  useEffect(load, [load]);

  useEffect(() => {
    if (active) endRef.current?.scrollIntoView({ block: "end" });
  }, [messages, active]);

  async function send(text) {
    const message = (text ?? input).trim();
    if (!message || busy) return;
    setInput("");
    setBusy(true);

    const pending = { role: "agent", content: "thinking…", pending: true };
    setMessages((prev) => [...prev, { role: "user", content: message }, pending]);

    try {
      const data = await api3.chat(message, id);
      setMessages((prev) =>
        prev.map((item) =>
          item === pending ? { role: "agent", content: data.answer || "(no answer)", details: data } : item,
        ),
      );
      setMemory(data.memory || {});
    } catch (error) {
      setMessages((prev) =>
        prev.map((item) =>
          item === pending
            ? { role: "agent", content: `The request failed: ${error.message}` }
            : item,
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  async function forget() {
    setBusy(true);
    try {
      await api3.clearSession(id);
      setMemory({});
      setMessages([]);
    } catch (error) {
      setMessages((prev) => [...prev, { role: "agent", content: `Could not clear memory: ${error.message}` }]);
    } finally {
      setBusy(false);
    }
  }

  if (health.status === "down") {
    return (
      <section hidden={!active} className="p-6">
        <UnavailableCard onRetry={load} />
      </section>
    );
  }

  return (
    <section
      hidden={!active}
      className="mx-auto grid w-full max-w-[1240px] grid-cols-1 items-start gap-5 p-6 lg:grid-cols-[1fr_minmax(260px,320px)]"
    >
      <Card className="min-h-[520px]">
        <CardHeader>
          <CardTitle>Conversation</CardTitle>
          {health.status === "loading" ? (
            <span className="flex items-center gap-2 text-caption-1-regular text-text-secondary">
              <Spinner /> starting the agent…
            </span>
          ) : (
            <span className="text-caption-1-regular text-text-secondary">
              {health.data.document} · {health.data.chunks} chunks · llm: {health.data.llm_backend}
              {health.data.llm_model ? `/${health.data.llm_model}` : ""}
            </span>
          )}
        </CardHeader>
        <CardContent className="flex min-h-0 flex-col gap-3.5">
          <div className="flex min-h-[340px] max-h-[calc(100vh-360px)] flex-col gap-3.5 overflow-y-auto pr-1">
            {messages.length === 0 ? (
              <p className="text-body-2-regular italic text-text-secondary">
                Ask about plans, pricing, storage or SLA credits.
              </p>
            ) : (
              messages.map((message, index) => <Bubble key={index} message={message} />)
            )}
            <div ref={endRef} />
          </div>

          <div className="flex flex-wrap gap-1.5">
            {SUGGESTIONS.map((suggestion) => (
              <Button
                key={suggestion}
                variant="secondary"
                size="xs"
                onClick={() => send(suggestion)}
                disabled={busy}
                title={suggestion}
                className="max-w-[290px]"
              >
                <span className="truncate">
                  {suggestion.length > 52 ? `${suggestion.slice(0, 50)}…` : suggestion}
                </span>
              </Button>
            ))}
          </div>

          <form
            className="flex gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              send();
            }}
          >
            <TextField
              value={input}
              onChange={setInput}
              aria-label="Message"
              isDisabled={busy}
              className="w-full"
            >
              <InputBase
                placeholder="Ask about plans, pricing, storage, SLA credits…"
                autoComplete="off"
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    send();
                  }
                }}
              />
            </TextField>
            <Button type="submit" leadingIcon={RiSendPlaneLine} disabled={busy || !input.trim()}>
              Send
            </Button>
          </form>
        </CardContent>
      </Card>

      <aside className="flex flex-col gap-4">
        <MemoryCard memory={memory} onForget={forget} busy={busy} />
        <SourceCard health={health.data} />
        <Card>
          <CardContent className="flex items-start gap-2 text-caption-1-regular text-text-secondary">
            <RiChat3Line className="mt-0.5 size-4 shrink-0" aria-hidden />
            <span>
              Session <code className="font-mono">{id}</code>. Memory is stored per session in{" "}
              <code className="font-mono">data/part3_sessions/</code>.
            </span>
          </CardContent>
        </Card>
      </aside>
    </section>
  );
}
