import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { Chip } from "@/components/base/badges/chip";
import { RowButton } from "./RowButton.jsx";
import { STATUS_COLOR } from "../constants.js";

const MSG_STATUS_LABEL = {
  queued: "queued",
  processing: "classifying…",
  skipped: "already processed",
  failed: "failed",
};

function FetchRow({ msg, onOpen }) {
  const label = msg.status === "done" ? (msg.action || "done").replace(/_/g, " ") : MSG_STATUS_LABEL[msg.status] || msg.status;
  const detail = msg.status === "failed" ? msg.error : msg.reason || "";
  const statusKey = msg.status === "done" ? msg.action : msg.status;

  return (
    <RowButton disabled={!msg.trace_id} onClick={() => onOpen(msg.trace_id)}>
      <span className="mb-1 flex items-center gap-2">
        <Chip variant="caption" color={STATUS_COLOR[statusKey]}>
          {label}
        </Chip>
        <span className="truncate text-body-semibold text-text-primary">{msg.subject}</span>
      </span>
      <span className="block break-words text-caption-1-regular text-text-secondary">
        {msg.sender}
        {detail ? ` · ${detail}` : ""}
      </span>
    </RowButton>
  );
}

export function FetchInbox({ job, onOpenTicket }) {
  const done = job.total - job.pending;
  const heading = job.finished ? `Fetched ${job.total} message(s) — all processed.` : `Processing ${done + 1} of ${job.total}…`;
  const pendingMessages = job.messages.filter((msg) => msg.status === "queued" || msg.status === "processing");

  return (
    <Card>
      <CardHeader>
        <CardTitle>Inbox fetch</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        <p className="text-caption-1-regular text-text-secondary">{heading}</p>
        <div className="flex flex-col gap-1.5">
          {pendingMessages.length ? (
            pendingMessages.map((msg) => (
              <FetchRow key={msg.trace_id || `${msg.sender}-${msg.subject}`} msg={msg} onOpen={onOpenTicket} />
            ))
          ) : (
            <p className="text-caption-1-regular text-text-secondary">Nothing pending.</p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
