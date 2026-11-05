import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { Spinner } from "@/components/base/spinner/spinner";
import { ProcessResult } from "./ProcessResult.jsx";
import { TicketDetail } from "./TicketDetail.jsx";
import { FetchInbox } from "./FetchInbox.jsx";

function EmptyCard({ children }) {
  return (
    <Card>
      <CardContent className="italic text-text-secondary">{children}</CardContent>
    </Card>
  );
}

export function OutPanel({ out, onOpenTicket }) {
  switch (out?.kind) {
    case "processing":
      return (
        <EmptyCard>
          <span className="flex items-center gap-2 not-italic text-text-primary">
            <Spinner /> Processing…
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
            <pre className="whitespace-pre-wrap rounded-xl bg-background-tertiary-error p-3 font-mono text-body-2-regular text-text-error-primary">
              {out.message}
            </pre>
          </CardContent>
        </Card>
      );
    case "ticket":
      return <TicketDetail ticket={out.ticket} onReplySent={onOpenTicket} />;
    case "fetch":
      return <FetchInbox job={out.job} onOpenTicket={onOpenTicket} />;
    default:
      return <EmptyCard>Process an email or pick a ticket to see its decision trail.</EmptyCard>;
  }
}
