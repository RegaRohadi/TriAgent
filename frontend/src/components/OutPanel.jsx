import { RiErrorWarningLine, RiMailOpenLine } from "@remixicon/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { Spinner } from "@/components/base/spinner/spinner";
import { EmptyState } from "./EmptyState.jsx";
import { ProcessResult } from "./ProcessResult.jsx";
import { TicketDetail } from "./TicketDetail.jsx";
import { FetchInbox } from "./FetchInbox.jsx";

function EmptyCard({ children }) {
  return (
    <Card>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

export function OutPanel({ out, onOpenTicket }) {
  switch (out?.kind) {
    case "processing":
      return (
        <EmptyCard>
          <span className="flex items-center gap-2 text-[13px] text-ink">
            <Spinner /> Processing… the agent is walking the pipeline.
          </span>
        </EmptyCard>
      );
    case "result":
      return <ProcessResult state={out.state} />;
    case "error":
      return (
        <Card>
          <CardHeader>
            <CardTitle>Error</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-start gap-2 rounded-xl border border-danger/25 bg-danger-soft p-3 text-danger">
              <RiErrorWarningLine className="mt-0.5 size-4 shrink-0" aria-hidden />
              <pre className="min-w-0 whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed">
                {out.message}
              </pre>
            </div>
          </CardContent>
        </Card>
      );
    case "ticket":
      return <TicketDetail ticket={out.ticket} onReplySent={onOpenTicket} />;
    case "fetch":
      return <FetchInbox job={out.job} onOpenTicket={onOpenTicket} />;
    default:
      return (
        <Card className="p-4 md:p-5">
          <EmptyState
            icon={RiMailOpenLine}
            title="No decision trail yet"
            description="Process an email or pick a ticket from the history. The outcome, pipeline flow, verification trail, and retrieved policy context will appear here."
          />
        </Card>
      );
  }
}
