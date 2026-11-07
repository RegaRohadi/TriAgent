import { ProcessForm } from "./ProcessForm.jsx";
import { TicketHistory } from "./TicketHistory.jsx";
import { OutPanel } from "./OutPanel.jsx";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { PageHeader, StatusBadge } from "./PageHeader.jsx";

const OFFLINE = "backend unavailable";

const GUIDE = [
  ["Outcome", "Auto-draft or route to a human, with the reason and priority."],
  ["Pipeline flow", "The eight-node spine, its branches, and per-node timing."],
  ["Decision trace", "Exact detail and elapsed time for every node that ran."],
  ["Retrieved context", "Policy chunks and similarity scores used to ground the reply."],
];

function backendBadge(meta) {
  if (!meta || meta === "loading…") {
    return <StatusBadge tone="neutral">Connecting…</StatusBadge>;
  }
  if (meta === OFFLINE) {
    return <StatusBadge tone="danger">Backend offline</StatusBadge>;
  }
  return <StatusBadge tone="success">Agents online</StatusBadge>;
}

function GuideCard() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>What you will see</CardTitle>
        <span className="text-[10.5px] font-medium text-ink-faint">after a run</span>
      </CardHeader>
      <CardContent>
        <ol className="grid gap-2.5 sm:grid-cols-2 xl:grid-cols-1">
          {GUIDE.map(([title, description], index) => (
            <li key={title} className="flex gap-2.5 text-[11px] leading-relaxed text-ink-soft">
              <span className="mt-0.5 grid size-4 shrink-0 place-items-center rounded-full bg-brand-soft text-[9px] font-bold text-brand">
                {index + 1}
              </span>
              <span>
                <b className="font-semibold text-ink">{title}.</b> {description}
              </span>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}

export function PartOnePanel({ active, meta, samples, onRun, running, history, fetchInbox, out, onOpenTicket }) {
  return (
    <section hidden={!active} className="fade-up flex flex-col gap-6">
      <PageHeader
        eyebrow="Mail · email agent"
        title="Triage, draft, and verify support email."
        description="The agent classifies incoming email, retrieves policy context, drafts a reply, then checks its own claims. Anything uncertain is routed to a human."
        meta={meta && meta !== "loading…" && meta !== OFFLINE ? meta : undefined}
        actions={backendBadge(meta)}
      />

      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(340px,400px)_minmax(0,1fr)]">
        <div className="contents min-w-0 xl:flex xl:flex-col xl:gap-4">
          <div className="order-1 min-w-0">
            <ProcessForm samples={samples} onRun={onRun} running={running} />
          </div>
          <div className="order-3 min-w-0">
            <TicketHistory
              data={history.historyData}
              statusFilter={history.statusFilter}
              onFilterChange={history.changeFilter}
              selectedTrace={history.selectedTrace}
              onOpenTicket={onOpenTicket}
              onFetchNow={fetchInbox.fetchNow}
              fetchStatus={fetchInbox.status}
              fetchBusy={fetchInbox.busy}
            />
          </div>
        </div>
        <div className="order-2 flex min-w-0 flex-col gap-4">
          <OutPanel out={out} onOpenTicket={onOpenTicket} />
          {!out && <GuideCard />}
        </div>
      </div>
    </section>
  );
}
