import { RiInboxArchiveLine } from "@remixicon/react";
import { Button } from "@/components/base/buttons/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { Chip } from "@/components/base/badges/chip";
import { Spinner } from "@/components/base/spinner/spinner";
import { PillTab, PillTabList } from "@/components/base/tabs/pill-tab";
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
          Fetch inbox now
        </Button>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {fetchStatus?.text && (
          <p className={`text-caption-1-regular ${NOTE_TONE[fetchStatus.kind] || NOTE_TONE.note}`}>{fetchStatus.text}</p>
        )}

        <PillTabList aria-label="Filter by status" className="flex-wrap">
          {filters.map(([value, label, n]) => (
            <PillTab key={value || "all"} variant="gray" isSelected={statusFilter === value} onSelect={() => onFilterChange(value)}>
              {label} <span className="text-text-tertiary">{n}</span>
            </PillTab>
          ))}
        </PillTabList>

        <div className="flex max-h-[62vh] flex-col gap-1.5 overflow-y-auto">
          {tickets.map((t) => (
            <RowButton key={t.trace_id} selected={selectedTrace === t.trace_id} onClick={() => onOpenTicket(t.trace_id)}>
              <span className="mb-1 flex items-center gap-2">
                <Chip variant="caption" color={STATUS_COLOR[t.status]}>
                  {STATUS_LABEL[t.status] || t.status}
                </Chip>
                <span className="truncate text-body-semibold text-text-primary">{t.subject || "(no subject)"}</span>
              </span>
              <span className="block break-words text-caption-1-regular text-text-secondary">
                {t.customer_email} · {t.route_reason || "handled"}
              </span>
            </RowButton>
          ))}
        </div>

        <p className="text-caption-1-regular text-text-secondary">
          {tickets.length
            ? `Showing ${tickets.length} ticket(s). Click one to see its decision trail.`
            : "No tickets recorded yet — process an email first."}
        </p>
      </CardContent>
    </Card>
  );
}
