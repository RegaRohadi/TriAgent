import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { Chip } from "@/components/base/badges/chip";
import { DecisionTrace, KnowledgeBaseContext } from "./DecisionTrace.jsx";
import { PipelineFlow } from "./PipelineFlow.jsx";

const SEND_NOTE = {
  sent: (sender) => <p className="font-mono text-[11px] text-success">✓ sent to {sender}</p>,
  smtp_not_configured: () => (
    <p className="font-mono text-[11px] leading-relaxed text-ink-faint">
      not sent — SMTP is not configured (set SMTP_* in .env to enable sending)
    </p>
  ),
  smtp_error: () => (
    <p className="font-mono text-[11px] leading-relaxed text-danger">
      send failed — SMTP is configured but the attempt errored, see server logs
    </p>
  ),
};

const PRE =
  "whitespace-pre-wrap break-words rounded-xl border border-line bg-surface-2 p-3 font-mono text-[11.5px] leading-relaxed text-ink";

export function ProcessResult({ state }) {
  const human = state.final_action === "route_to_human";
  const ranNodes = new Set((state.trace || []).map((e) => e.node));
  const cats = state.classification?.labels?.length ? (
    <span className="flex flex-wrap gap-1.5">
      {state.classification.labels.map((l, i) => (
        <Chip variant="caption" color="neutral" key={i}>
          {l.category} {l.confidence.toFixed(2)}
        </Chip>
      ))}
    </span>
  ) : (
    <span className="italic text-text-secondary">not classified — escalated before the classifier ran</span>
  );

  const sendNote = SEND_NOTE[state.send_status]?.(state.email?.sender) || null;

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Outcome</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <p className="flex flex-wrap items-center gap-2">
            <Chip color={human ? "rose" : "lime"}>{human ? "ROUTE TO HUMAN" : "AUTO DRAFT"}</Chip>
            <span className="font-mono text-[10.5px] break-all text-ink-faint">trace_id={state.trace_id}</span>
          </p>
          <div>{cats}</div>
          {human ? (
            <div className="rounded-xl border border-danger/25 bg-danger-soft px-3 py-2.5 text-[12px] leading-relaxed text-ink">
              <b>Routed to a human</b> — reason: <code>{state.route_reason}</code>, priority: <b>{state.priority}</b>
              {state.precheck_evidence ? (
                <>
                  <br />
                  evidence: <code>{state.precheck_evidence}</code>
                </>
              ) : null}
              {state.verification?.unsupported_claims?.length ? (
                <>
                  <br />
                  unsupported: {state.verification.unsupported_claims.join("; ")}
                </>
              ) : null}
              {state.draft ? (
                <>
                  <br />
                  <br />
                  <i>A draft was attempted and attached to the ticket:</i>
                  <pre className={`mt-1 ${PRE}`}>{state.draft.text}</pre>
                </>
              ) : null}
            </div>
          ) : (
            <>
              <pre className={PRE}>{state.draft?.text || ""}</pre>
              <p className="font-mono text-[10.5px] break-words text-ink-faint">
                citations: {(state.draft?.citations || []).join(", ")}
              </p>
              {sendNote}
            </>
          )}
        </CardContent>
      </Card>
      <PipelineFlow trace={state.trace} />
      <DecisionTrace trace={state.trace} />
      <KnowledgeBaseContext chunks={state.retrieved} retrieveRan={ranNodes.has("retrieve")} />
    </div>
  );
}
