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
      </CardHeader>
      <CardContent>
        <Table aria-label="Decision trace" size="sm" className="min-w-[520px]">
          <TableHeader>
            <TableColumn isRowHeader>Node</TableColumn>
            <TableColumn>Outcome</TableColumn>
            <TableColumn>Detail</TableColumn>
            <TableColumn>Time</TableColumn>
          </TableHeader>
          <TableBody>
            {(trace || []).map((ev, i) => (
              <TableRow key={i} id={i}>
                <TableCell className="font-semibold whitespace-nowrap">{ev.node}</TableCell>
                <TableCell>
                  <Chip variant="caption" color={HIT_PATTERN.test(ev.outcome) ? "rose" : "lime"}>
                    {ev.outcome}
                  </Chip>
                </TableCell>
                <TableCell className="font-mono text-caption-1-regular! text-text-secondary!">{traceDetail(ev.detail)}</TableCell>
                <TableCell className="text-right whitespace-nowrap text-text-secondary!">{ev.elapsed_ms}ms</TableCell>
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
      <div key={i} className="rounded-r-xl border-l-2 border-accent-500 bg-background-secondary-default px-3 py-2 text-body-2-regular">
        <div className="mb-1 text-caption-1-regular text-text-secondary">
          {c.doc_id} §{c.section} · similarity {c.score.toFixed(3)}
        </div>
        {c.text.slice(0, maxLen)}
        {c.text.length > maxLen ? "…" : ""}
      </div>
    ));
  } else if (emptyText) {
    body = <div className="italic text-text-secondary">{emptyText}</div>;
  } else if (retrieveRan) {
    body = (
      <div className="italic text-text-secondary">
        No chunk passed the similarity floor — an empty result is itself an escalation trigger.
      </div>
    );
  } else {
    body = <div className="italic text-text-secondary">Retrieval never ran: the email was escalated earlier in the pipeline.</div>;
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
