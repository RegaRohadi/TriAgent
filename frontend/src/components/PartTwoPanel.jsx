import { useCallback, useEffect, useRef, useState } from "react";
import {
  RiArrowRightUpLine,
  RiContrastLine,
  RiGlobalLine,
  RiPlayLine,
  RiRefreshLine,
} from "@remixicon/react";
import { api2 } from "../api2.js";
import { apiBase } from "../backend.js";
import { Button } from "@/components/base/buttons/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { Chip } from "@/components/base/badges/chip";
import { Input, InputBase, TextField } from "@/components/base/input/input";
import { Label } from "@/components/base/input/label";
import { Spinner } from "@/components/base/spinner/spinner";
import { EmptyState } from "./EmptyState.jsx";
import { PageHeader, StatusBadge } from "./PageHeader.jsx";

const EXAMPLES = [
  ["Wikipedia · RAG", "https://en.wikipedia.org/wiki/Retrieval-augmented_generation"],
  ["Wikipedia · Web scraping", "https://en.wikipedia.org/wiki/Web_scraping"],
];

const STEPS = [
  "Fetch the URL with a timeout and content-type check.",
  "Strip navigation, scripts, and chrome.",
  "Map each chunk through the model, then reduce.",
  "Enforce the word budget and rewrite if needed.",
];

const fmt = (n) => Number(n || 0).toLocaleString("en-US");
const pct = (x) => `${Math.round((x || 0) * 100)}%`;
const secs = (ms) => `${((ms || 0) / 1000).toFixed(1)} s`;

function MetricRow({ label, children }) {
  return (
    <tr className="border-b border-line last:border-0">
      <th className="w-[36%] px-2 py-2 text-left align-top text-[10.5px] font-semibold tracking-wide text-ink-faint uppercase">
        {label}
      </th>
      <td className="px-2 py-2 align-top text-[12px] leading-relaxed text-ink-soft">{children}</td>
    </tr>
  );
}

function MetricsTable({ result }) {
  const smaller = result.raw_bytes ? 1 - result.extracted_chars / result.raw_bytes : 0;
  return (
    <table className="w-full border-collapse">
      <tbody>
        <MetricRow label="Fetched">{fmt(result.raw_bytes)} bytes</MetricRow>
        <MetricRow label="Sent to model">
          {fmt(result.extracted_chars)} chars — {pct(smaller)} smaller than the raw page
        </MetricRow>
        <MetricRow label="Extraction">
          {result.extraction_strategy} · {pct(result.reduction_ratio)} of the page&apos;s text dropped as
          navigation and chrome
        </MetricRow>
        <MetricRow label="Summarization">
          {result.strategy === "map_reduce"
            ? `map-reduce · ${result.chunk_count} chunks · ${result.reduce_rounds} extra reduce round(s)`
            : "single pass — the page fit in one chunk"}
        </MetricRow>
        <MetricRow label="Model calls">{fmt(result.llm_calls)}</MetricRow>
        <MetricRow label="Guardrail">
          {result.guardrail_enforced_by}
          {result.guardrail_attempts ? ` · ${result.guardrail_attempts} rewrite(s)` : ""}
        </MetricRow>
        <MetricRow label="Elapsed">{secs(result.elapsed_ms)}</MetricRow>
      </tbody>
    </table>
  );
}

function SummaryBlock({ result, budget }) {
  return (
    <div className="flex flex-col gap-3">
      <a
        href={result.url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1 text-[13px] font-semibold break-words text-brand hover:underline"
      >
        {result.title}
        <RiArrowRightUpLine className="size-4 shrink-0" aria-hidden />
      </a>
      <div className="flex flex-wrap items-center gap-2">
        <Chip color={result.within_budget ? "lime" : "rose"}>
          {result.word_count} / {budget} words
        </Chip>
        <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-[10px] font-semibold text-ink-faint">
          enforced by: {result.guardrail_enforced_by}
        </span>
      </div>
      <p className="whitespace-pre-wrap text-[12.5px] leading-relaxed text-ink-soft">{result.summary}</p>
      {result.key_points?.length ? (
        <ul className="list-disc space-y-1 pl-5 text-[12px] leading-relaxed text-ink-soft">
          {result.key_points.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

function SummaryCard({ result, budget }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Summary</CardTitle>
        <Chip variant="caption" color="blue">
          {result.word_count} words
        </Chip>
      </CardHeader>
      <CardContent>
        <SummaryBlock result={result} budget={budget} />
      </CardContent>
    </Card>
  );
}

function MetricsCard({ result }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>What the pipeline did</CardTitle>
      </CardHeader>
      <CardContent>
        <MetricsTable result={result} />
      </CardContent>
    </Card>
  );
}

function Failure({ title, elapsed, error }) {
  return (
    <div className="flex flex-col gap-1 rounded-xl border border-danger/25 bg-danger-soft p-3 text-[12px] leading-relaxed text-ink">
      <strong className="text-danger">{title}</strong>
      {elapsed ? <span className="text-[10.5px] text-ink-faint">after {secs(elapsed)}</span> : null}
      <code className="font-mono text-[10.5px] break-words">{error}</code>
    </div>
  );
}

function CompareView({ data, budget }) {
  const naive = data.naive;
  const fixed = data.fixed;

  return (
    <div className="grid grid-cols-1 items-start gap-4 xl:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle>Before — naive_scraper.py</CardTitle>
          <Chip variant="caption" color="rose">
            no guardrail
          </Chip>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {naive.error ? (
            <Failure title="Failed" elapsed={naive.elapsed_ms} error={naive.error} />
          ) : (
            <>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-[10px] font-semibold text-ink-faint">
                  {naive.word_count} words · no length check
                </span>
                <span className="rounded-md bg-surface-2 px-1.5 py-0.5 text-[10px] font-semibold text-ink-faint">
                  {secs(naive.elapsed_ms)}
                </span>
              </div>
              <p className="whitespace-pre-wrap text-[12px] leading-relaxed text-ink-soft">{naive.summary}</p>
            </>
          )}
          <p className="text-[10.5px] leading-relaxed text-ink-faint">
            No timeout, no status or content-type check, the whole DOM in one prompt, no length check.
            A fluent summary here is not proof it read the right page.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>After — pipeline.py</CardTitle>
          <Chip variant="caption" color="lime">
            guarded
          </Chip>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {fixed.error ? (
            <Failure title="Failed" error={fixed.error} />
          ) : (
            <>
              <SummaryBlock result={fixed.result} budget={budget} />
              <MetricsTable result={fixed.result} />
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function UnavailableCard({ onRetry }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Lens is not running</CardTitle>
        <StatusBadge tone="danger">Offline</StatusBadge>
      </CardHeader>
      <CardContent className="flex flex-col items-start gap-3">
        <p>
          Nothing answered at <code className="font-mono text-[11px]">{apiBase("part2")}</code>. Start it with:
        </p>
        <pre className="w-full overflow-x-auto rounded-xl border border-line bg-surface-2 p-3 font-mono text-[11px] text-ink">
          docker compose up -d scraper
        </pre>
        <p className="text-[10.5px] leading-relaxed text-ink-faint">
          Without Docker: <code className="font-mono">uvicorn part2_scraper.web:app --port 8002</code>
        </p>
        <Button variant="secondary" size="small" leadingIcon={RiRefreshLine} onClick={onRetry}>
          Try again
        </Button>
      </CardContent>
    </Card>
  );
}

function healthBadge(health) {
  if (health.status === "loading") return <StatusBadge tone="neutral">Connecting…</StatusBadge>;
  if (health.status === "up") return <StatusBadge tone="success">Lens online</StatusBadge>;
  return <StatusBadge tone="danger">Lens offline</StatusBadge>;
}

export function PartTwoPanel({ active }) {
  const [url, setUrl] = useState("");
  const [budget, setBudget] = useState("");
  const [health, setHealth] = useState({ status: "loading", data: null });
  const [out, setOut] = useState({ kind: "idle" });
  const [busy, setBusy] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const ticker = useRef(null);
  const autoRan = useRef(false);

  const loadHealth = useCallback(() => {
    setHealth({ status: "loading", data: null });
    api2
      .health()
      .then((data) => {
        setHealth({ status: "up", data });
        setBudget((current) => current || String(data.summary_max_words));
      })
      .catch(() => setHealth({ status: "down", data: null }));
  }, []);

  useEffect(loadHealth, [loadHealth]);

  useEffect(() => {
    if (health.status !== "up" || autoRan.current) return;
    autoRan.current = true;
    const params = new URLSearchParams(location.search);
    const wanted = params.get("p2url") || params.get("url");
    const run = params.get("p2run") || params.get("run");
    const max = params.get("max") || params.get("p2max");
    if (wanted) setUrl(wanted);
    if (max) setBudget(max);
    if (wanted && (run === "summarize" || run === "compare")) {
      runJob(run, wanted, max || String(health.data?.summary_max_words || ""));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [health.status]);

  useEffect(() => () => clearInterval(ticker.current), []);

  function startTicker() {
    const started = Date.now();
    setElapsed(0);
    clearInterval(ticker.current);
    ticker.current = setInterval(() => setElapsed(Math.round((Date.now() - started) / 1000)), 1000);
  }

  function stopTicker() {
    clearInterval(ticker.current);
    ticker.current = null;
  }

  async function runJob(mode, targetUrl, targetBudget) {
    const trimmed = (targetUrl ?? url).trim();
    if (!trimmed || busy) return;
    const parsed = parseInt(targetBudget ?? budget, 10);
    const maxWords = Number.isFinite(parsed) ? parsed : null;

    setBusy(true);
    setOut({ kind: "working", mode });
    startTicker();
    try {
      const data =
        mode === "compare"
          ? await api2.compare({ url: trimmed, max_words: maxWords })
          : await api2.summarize({ url: trimmed, max_words: maxWords });
      stopTicker();
      setOut({
        kind: mode === "compare" ? "compare" : "summary",
        data,
        budget: maxWords ?? health.data?.summary_max_words ?? "",
      });
    } catch (error) {
      stopTicker();
      setOut({ kind: "error", message: error.message });
    } finally {
      setBusy(false);
    }
  }

  function renderOutput() {
    switch (out.kind) {
      case "working":
        return (
          <Card>
            <CardHeader>
              <CardTitle>{out.mode === "compare" ? "Comparing before and after" : "Summarizing"}</CardTitle>
              <Chip variant="caption" color="blue">
                {elapsed} s
              </Chip>
            </CardHeader>
            <CardContent className="flex flex-col gap-2">
              <span className="flex items-center gap-2 text-ink">
                <Spinner /> Working…
              </span>
              <p className="text-[10.5px] leading-relaxed text-ink-faint">
                Fetch → extract → one model call per chunk → merge → length check. With a live model
                this usually takes 10–60 s.
              </p>
            </CardContent>
          </Card>
        );
      case "summary":
        return (
          <div className="flex flex-col gap-4">
            <SummaryCard result={out.data} budget={out.budget} />
            <MetricsCard result={out.data} />
          </div>
        );
      case "compare":
        return <CompareView data={out.data} budget={out.budget} />;
      case "error":
        return (
          <Card>
            <CardHeader>
              <CardTitle>Could not summarize</CardTitle>
              <StatusBadge tone="danger">Failed</StatusBadge>
            </CardHeader>
            <CardContent>
              <Failure title="Request failed" error={out.message} />
            </CardContent>
          </Card>
        );
      default:
        return (
          <Card className="p-4 md:p-5">
            <EmptyState
              icon={RiGlobalLine}
              title="Give Lens a page to read"
              description="Paste a public URL, choose a word budget, and run. The summary, the pipeline metrics, and an optional before/after comparison will show up here."
            />
          </Card>
        );
    }
  }

  const healthMeta =
    health.status === "up"
      ? `llm: ${health.data.llm_backend}${health.data.llm_model ? `/${health.data.llm_model}` : ""} · chunks of ${
          health.data.chunk_max_tokens
        } tokens · ${health.data.map_workers} parallel map calls`
      : undefined;

  return (
    <section hidden={!active} className="fade-up flex flex-col gap-6">
      <PageHeader
        eyebrow="Lens · scrape & summarize"
        title="Read the page, not the chrome."
        description="Fetches a URL, strips navigation, maps chunks through the model, and enforces a word budget — with a before/after comparison against a naive scraper."
        meta={healthMeta}
        actions={healthBadge(health)}
      />

      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(320px,380px)_minmax(0,1fr)]">
        <div className="contents min-w-0 xl:flex xl:flex-col xl:gap-4">
          <div className="order-1 min-w-0">
            <Card>
              <CardHeader>
                <CardTitle>Page to summarize</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-4">
                <Input
                  label="URL"
                  placeholder="https://en.wikipedia.org/wiki/…"
                  leadingIcon={RiGlobalLine}
                  value={url}
                  onChange={setUrl}
                  autoComplete="off"
                />

                <div className="flex flex-wrap gap-1">
                  {EXAMPLES.map(([label, example]) => (
                    <Button
                      key={label}
                      variant="ghost"
                      size="xs"
                      onClick={() => setUrl(example)}
                      className="text-ink-soft"
                    >
                      {label}
                    </Button>
                  ))}
                </div>

                <TextField
                  value={budget}
                  onChange={setBudget}
                  isDisabled={health.status !== "up"}
                  className="w-full"
                >
                  <Label>Word budget</Label>
                  <InputBase inputMode="numeric" placeholder="100" />
                </TextField>

                <div className="flex flex-col gap-2">
                  <Button
                    leadingIcon={RiPlayLine}
                    onClick={() => runJob("summarize")}
                    disabled={busy || health.status !== "up" || !url.trim()}
                    className="w-full"
                  >
                    Summarize
                  </Button>
                  <Button
                    variant="secondary"
                    leadingIcon={RiContrastLine}
                    onClick={() => runJob("compare")}
                    disabled={busy || health.status !== "up" || !url.trim()}
                    className="w-full"
                  >
                    Compare before / after
                  </Button>
                </div>

                <p className="text-[10.5px] leading-relaxed text-ink-faint">
                  Compare runs <code className="font-mono">naive_scraper.py</code> and the fixed pipeline on
                  the same page, side by side.
                </p>
              </CardContent>
            </Card>
          </div>

          <div className="order-3 min-w-0">
            <Card>
              <CardHeader>
                <CardTitle>What happens</CardTitle>
              </CardHeader>
              <CardContent>
                <ol className="space-y-2.5">
                  {STEPS.map((step, index) => (
                    <li key={step} className="flex gap-2.5 text-[11px] leading-relaxed text-ink-soft">
                      <span className="mt-0.5 grid size-4 shrink-0 place-items-center rounded-full bg-surface-2 text-[9px] font-bold text-ink-faint">
                        {index + 1}
                      </span>
                      {step}
                    </li>
                  ))}
                </ol>
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="order-2 flex min-w-0 flex-col gap-4">
          {health.status === "down" ? <UnavailableCard onRetry={loadHealth} /> : renderOutput()}
        </div>
      </div>
    </section>
  );
}
