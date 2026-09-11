import { ProcessForm } from "./ProcessForm.jsx";
import { TicketHistory } from "./TicketHistory.jsx";
import { OutPanel } from "./OutPanel.jsx";

export function PartOnePanel({ active, samples, onRun, running, history, fetchInbox, out, onOpenTicket }) {
  return (
    <section hidden={!active} className="grid grid-cols-1 items-start gap-5 p-6 lg:grid-cols-[minmax(320px,420px)_1fr]">
      <div className="flex flex-col gap-4">
        <ProcessForm samples={samples} onRun={onRun} running={running} />
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
      <OutPanel out={out} onOpenTicket={onOpenTicket} />
    </section>
  );
}
