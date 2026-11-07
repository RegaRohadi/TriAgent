import { RiInboxArchiveLine } from "@remixicon/react";
import { Button } from "@/components/base/buttons/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { Chip } from "@/components/base/badges/chip";
import { Spinner } from "@/components/base/spinner/spinner";
import { RowButton } from "./RowButton.jsx";
import { NOTE_TONE, STATUS_COLOR, STATUS_LABEL } from "../constants.js";

export function TicketHistory({ data, statusFilter, onFilterChange, selectedTrace, onOpenTicket, onFetchNow, fetchStatus, fetchBusy }) {
  const counts = data?.counts || {};
  const tickets = data?.tickets || [];
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const filters = [["", "all", total], ...Object.entries(counts).map(([s, n]) => [s, STATUS_LABEL[s] || s, n])];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ticket history</CardTitle>
        <Button
          size="small"
          variant="secondary"
          onClick={onFetchNow}
          disabled={fetchBusy}
          leadingIcon={fetchBusy ? Spinner : RiInboxArchiveLine}
        >
          {fetchBusy ? "Fetching…" : "Fetch inbox now"}
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {fetchStatus?.text && (
          <p className={`text-[11px] leading-relaxed ${NOTE_TONE[fetchStatus.kind] || NOTE_TONE.note}`}>
            {fetchStatus.text}
          </p>
        )}

        <div role="group" aria-label="Filter by status" className="flex flex-wrap gap-1.5">
          {filters.map(([value, label, n]) => {
            const selected = statusFilter === value;
            return (
              <button
                key={value || "all"}
                type="button"
                aria-pressed={selected}
                onClick={() => onFilterChange(value)}
                className={`inline-flex cursor-pointer items-center gap-1.5 rounded-full border px-3 py-1.5 text-[11px] font-semibold transition-colors outline-none focus-visible:ring-2 focus-visible:ring-brand/35 ${
                  selected
                    ? "border-ink bg-ink text-surface"
                    : "border-line bg-surface text-ink-soft hover:border-line-strong hover:text-ink"
                }`}
              >
                {label}
                <span className={`text-[10px] font-bold ${selected ? "text-surface/70" : "text-ink-faint"}`}>{n}</span>
              </button>
            );
          })}
        </div>

        <div className="-mx-1 flex max-h-[48vh] flex-col gap-1.5 overflow-y-auto px-1 lg:max-h-[56vh]">
          {tickets.map((t) => (
            <RowButton key={t.trace_id} selected={selectedTrace === t.trace_id} onClick={() => onOpenTicket(t.trace_id)}>
              <span className="mb-1 flex min-w-0 items-center gap-2">
                <Chip variant="caption" color={STATUS_COLOR[t.status]}>
                  {STATUS_LABEL[t.status] || t.status}
                </Chip>
                <span className="truncate text-[12px] font-semibold text-ink">{t.subject || "(no subject)"}</span>
              </span>
              <span className="block break-words text-[10.5px] leading-relaxed text-ink-faint">
                {t.customer_email} · {t.route_reason || "handled"}
              </span>
            </RowButton>
          ))}
          {!tickets.length && (
            <p className="rounded-xl border border-dashed border-line px-3 py-6 text-center text-[11px] leading-relaxed text-ink-faint">
              No tickets recorded yet — process an email first.
            </p>
          )}
        </div>

        <p className="text-[10.5px] leading-relaxed text-ink-faint">
          {tickets.length
            ? `Showing ${tickets.length} ticket(s). Click one to see its decision trail.`
            : "History appears here after the agent handles an email."}
        </p>
      </CardContent>
    </Card>
  );
}
