import { RiArrowRightLine } from "@remixicon/react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { cx } from "@/utils/cx";

const SPINE = [
  { key: "triage", label: "Triage" },
  { key: "precheck", label: "Precheck" },
  { key: "classify", label: "Classify" },
  { key: "retrieve", label: "Retrieve" },
  { key: "refund_guard", label: "Refund guard" },
  { key: "draft_reply", label: "Draft reply" },
  { key: "verify", label: "Verify" },
  { key: "auto_reply", label: "Auto reply" },
];

const HIT_PATTERN = /critical|frequent|threshold|ungrounded|invalid|no_context|incomplete|low_confidence|error/;

const NODE_W = 118;
const ARROW_W = 28;
const STEP = NODE_W + ARROW_W;

const STATUS_STYLE = {
  success: "border-success/25 bg-success-soft text-success",
  danger: "border-danger/25 bg-danger-soft text-danger",
  neutral: "border-line bg-surface-2 text-ink-soft",
  pending: "border-dashed border-line-strong text-ink-faint",
};

function traceDetail(detail) {
  return Object.entries(detail || {})
    .filter(([, v]) => v !== null && v !== "" && !(Array.isArray(v) && !v.length))
    .map(([k, v]) => `${k}=${Array.isArray(v) ? v.join("|") : v}`)
    .join("  ");
}

function NodeBox({ label, status, outcome, elapsedMs, detail }) {
  return (
    <div
      style={{ width: NODE_W }}
      className={cx("shrink-0 rounded-lg border px-2 py-1.5 text-center", STATUS_STYLE[status])}
      title={detail ? traceDetail(detail) : undefined}
    >
      <div className="truncate text-[10.5px] font-semibold">{label}</div>
      {outcome ? <div className="mt-0.5 truncate text-[9.5px] font-medium opacity-90">{outcome}</div> : null}
      {elapsedMs != null ? <div className="text-[9px] opacity-70">{elapsedMs}ms</div> : null}
    </div>
  );
}

function Arrow({ dim }) {
  return (
    <div
      style={{ width: ARROW_W }}
      className={cx("flex shrink-0 items-center justify-center text-ink-faint", dim && "opacity-40")}
    >
      <RiArrowRightLine aria-hidden className="size-4" />
    </div>
  );
}

export function PipelineFlow({ trace }) {
  if (!trace?.length) return null;

  const byNode = new Map(trace.map((ev) => [ev.node, ev]));
  const lastEvent = trace[trace.length - 1];

  let branch = null;
  if (lastEvent.node === "route_human") {
    const prevEvent = trace[trace.length - 2];
    const fromIndex = SPINE.findIndex((n) => n.key === prevEvent?.node);
    branch = { fromIndex: Math.max(fromIndex, 0), label: "Route to human", event: lastEvent, status: "danger" };
  } else if (lastEvent.node === "triage" && lastEvent.outcome !== "customer_email") {
    branch = { fromIndex: 0, label: "Ignored (end)", event: lastEvent, status: "neutral" };
  }

  const lastRanIndex = branch ? branch.fromIndex : SPINE.reduce((max, n, i) => (byNode.has(n.key) ? i : max), -1);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Pipeline flow</CardTitle>
        <span className="text-[10.5px] font-medium text-ink-faint">spine · scroll →</span>
      </CardHeader>
      <CardContent>
        <div className="-mx-1 overflow-x-auto px-1 pb-1">
          <div className="flex w-max items-center">
            {SPINE.map((n, i) => {
              const ev = byNode.get(n.key);
              const isBranchPoint = branch && i === branch.fromIndex;
              const status = !ev ? "pending" : isBranchPoint && HIT_PATTERN.test(ev.outcome) ? "danger" : "success";
              return (
                <div key={n.key} className="flex shrink-0 items-center">
                  <NodeBox label={n.label} status={status} outcome={ev?.outcome} elapsedMs={ev?.elapsed_ms} detail={ev?.detail} />
                  {i < SPINE.length - 1 ? <Arrow dim={i >= lastRanIndex} /> : null}
                </div>
              );
            })}
          </div>
          {branch ? (
            <div style={{ marginLeft: branch.fromIndex * STEP + NODE_W / 2 - 1 }} className="flex w-max flex-col items-start">
              <div className="h-4 w-0.5 bg-current text-ink-faint" />
              <div className="-ml-[6px] text-ink-faint">▾</div>
            </div>
          ) : null}
          {branch ? (
            <div style={{ marginLeft: branch.fromIndex * STEP }} className="w-max">
              <NodeBox
                label={branch.label}
                status={branch.status}
                outcome={branch.event.outcome}
                elapsedMs={branch.event.elapsed_ms}
                detail={branch.event.detail}
              />
            </div>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
