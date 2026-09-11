import { useState } from "react";
import { RiSendPlaneLine } from "@remixicon/react";
import { Button } from "@/components/base/buttons/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { Chip } from "@/components/base/badges/chip";
import { TextArea } from "@/components/base/input/textarea";
import { api } from "../api.js";
import { DecisionTrace, KnowledgeBaseContext } from "./DecisionTrace.jsx";
import { PipelineFlow } from "./PipelineFlow.jsx";
import { NOTE_TONE, STATUS_COLOR, STATUS_LABEL } from "../constants.js";

const PRE = "whitespace-pre-wrap rounded-xl bg-background-secondary-default p-3 font-mono text-body-2-regular text-text-primary";

export function TicketDetail({ ticket, onReplySent }) {
  const p = ticket.payload || {};
  const email = p.email || {};
  const draft = p.draft_attempt;

  const [replyText, setReplyText] = useState(draft ? draft.text : "");
  const [sending, setSending] = useState(false);
  const [replyStatus, setReplyStatus] = useState(null);

  async function sendReply() {
    const text = replyText.trim();
    if (!text) {
      setReplyStatus({ kind: "err", text: "Reply is empty." });
      return;
    }
    setSending(true);
    setReplyStatus({ kind: "note", text: "Sending…" });
    try {
      const data = await api.replyAsHuman(ticket.trace_id, text);
      setReplyStatus(
        data.sent
          ? { kind: "ok", text: "Sent. Ticket marked resolved." }
          : { kind: "err", text: `Not sent (${data.send_status}) — ticket still marked resolved. ${data.detail || ""}` }
      );
      setTimeout(() => onReplySent(ticket.trace_id), 700);
    } catch (err) {
      setReplyStatus({ kind: "err", text: err.message });
      setSending(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Ticket</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          <p className="flex flex-wrap items-center gap-2">
            <Chip variant="caption" color={STATUS_COLOR[ticket.status]}>
              {STATUS_LABEL[ticket.status] || ticket.status}
            </Chip>
            <span className="font-mono text-caption-1-regular text-text-secondary">
              trace_id={ticket.trace_id} · {ticket.created_at}
            </span>
          </p>
          <p className="font-mono text-caption-1-regular text-text-secondary">
            from {ticket.customer_email} · reason: <code>{ticket.route_reason || "-"}</code> · priority: {ticket.priority}
          </p>
          <h3 className="mt-2 text-body-semibold text-text-primary">Customer email</h3>
          <pre className={PRE}>{(email.subject ? `Subject: ${email.subject}\n\n` : "") + (email.body || "")}</pre>
        </CardContent>
      </Card>

      {ticket.status === "open" && (
        <Card>
          <CardHeader>
            <CardTitle>Reply as a human agent</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {draft && (
              <p className="text-caption-1-regular text-text-secondary">
                Pre-filled with the draft the agent produced but did not send. Edit before sending.
              </p>
            )}
            <TextArea aria-label="Reply" rows={8} value={replyText} onChange={setReplyText} />
            <Button onClick={sendReply} disabled={sending} leadingIcon={RiSendPlaneLine} className="self-start">
              Send reply to {email.sender || ""}
            </Button>
            {replyStatus && (
              <p className={`text-caption-1-regular ${NOTE_TONE[replyStatus.kind] || NOTE_TONE.note}`}>{replyStatus.text}</p>
            )}
          </CardContent>
        </Card>
      )}

      {ticket.reply_text && (
        <Card>
          <CardHeader>
            <CardTitle>Reply that was sent</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            <p className="font-mono text-caption-1-regular text-text-secondary">
              by <b>{ticket.replied_by || "?"}</b> · {ticket.replied_at || ""} · delivery: <code>{ticket.send_status || "n/a"}</code>
            </p>
            <pre className={PRE}>{ticket.reply_text}</pre>
          </CardContent>
        </Card>
      )}

      <PipelineFlow trace={p.trace} />
      <DecisionTrace trace={p.trace} />
      <KnowledgeBaseContext chunks={p.retrieved} maxLen={260} emptyText="No knowledge base context was retrieved." />
    </div>
  );
}
