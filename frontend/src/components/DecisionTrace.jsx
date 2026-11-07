import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { Chip } from "@/components/base/badges/chip";
import { Table, TableBody, TableCell, TableColumn, TableHeader, TableRow } from "@/components/base/table/table";

const HIT_PATTERN = /critical|frequent|threshold|ungrounded|invalid|no_context|incomplete|low_confidence|error|queued/;

function traceDetail(detail) {
  return Object.entries(detail || {})
    .filter(([, v]) => v !== null && v !== "" && !(Array.isArray(v) && !v.length))
    .map(([k, v]) => `${k}=${Array.isArray(v) ? v.join("|") : v}`)
    .join("  ");
}

export function DecisionTrace({ trace }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Decision trace</CardTitle>
        <span className="text-[10.5px] font-medium text-ink-faint">{(trace || []).length} event(s)</span>
      </CardHeader>
      <CardContent>
        <Table aria-label="Decision trace" size="sm" className="min-w-[560px]">
          <TableHeader>
            <TableColumn isRowHeader>Node</TableColumn>
            <TableColumn>Outcome</TableColumn>
            <TableColumn>Detail</TableColumn>
            <TableColumn>Time</TableColumn>
          </TableHeader>
          <TableBody>
            {(trace || []).map((ev, i) => (
              <TableRow key={i} id={i}>
                <TableCell className="font-semibold whitespace-nowrap text-ink">{ev.node}</TableCell>
                <TableCell>
                  <Chip variant="caption" color={HIT_PATTERN.test(ev.outcome) ? "rose" : "lime"}>
                    {ev.outcome}
                  </Chip>
                </TableCell>
                <TableCell className="font-mono text-[10.5px]! text-ink-faint!">{traceDetail(ev.detail)}</TableCell>
                <TableCell className="text-right whitespace-nowrap text-ink-faint!">{ev.elapsed_ms}ms</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

export function KnowledgeBaseContext({ chunks, retrieveRan, maxLen = 320, emptyText }) {
  let body;
  if (chunks && chunks.length) {
    body = chunks.map((c, i) => (
      <div
        key={i}
        className="rounded-xl border border-line bg-surface-2 px-3 py-2 text-[12px] leading-relaxed text-ink-soft"
      >
        <div className="mb-1 text-[10.5px] font-medium text-ink-faint">
          {c.doc_id} §{c.section} · similarity {c.score.toFixed(3)}
        </div>
        {c.text.slice(0, maxLen)}
        {c.text.length > maxLen ? "…" : ""}
      </div>
    ));
  } else if (emptyText) {
    body = <div className="text-[12px] text-ink-faint italic">{emptyText}</div>;
  } else if (retrieveRan) {
    body = (
      <div className="text-[12px] leading-relaxed text-ink-faint italic">
        No chunk passed the similarity floor — an empty result is itself an escalation trigger.
      </div>
    );
  } else {
    body = (
      <div className="text-[12px] leading-relaxed text-ink-faint italic">
        Retrieval never ran: the email was escalated earlier in the pipeline.
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Retrieved knowledge base context</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">{body}</CardContent>
    </Card>
  );
}
