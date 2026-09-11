import { useCallback, useEffect, useRef, useState } from "react";
import { RiRefreshLine } from "@remixicon/react";
import { Button } from "@/components/base/buttons/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/base/card/card";
import { Spinner } from "@/components/base/spinner/spinner";

const COMPANIONS = {
  part2: { title: "Part 2 · Scrape & summarize", compose: "docker compose up -d scraper", local: "uvicorn part2_scraper.web:app --port 8002" },
  part3: { title: "Part 3 · Document chat", compose: "docker compose up -d chat", local: "uvicorn part3_doc_agent.web:app --port 8001" },
};

function companionUrl(tab, ports) {
  const port = ports[tab];
  return port ? `${location.protocol}//${location.hostname}:${port}/` : null;
}

function companionSrc(tab, base) {
  const src = new URL(base);
  const params = new URLSearchParams(location.search);
  if (tab === "part2") {
    if (params.get("p2url")) src.searchParams.set("url", params.get("p2url"));
    if (params.get("p2run")) src.searchParams.set("run", params.get("p2run"));
  }
  return src.toString();
}

export function CompanionPanel({ tab, ports, theme }) {
  const info = COMPANIONS[tab];
  const [state, setState] = useState("idle");
  const [retryTick, setRetryTick] = useState(0);
  const iframeRef = useRef(null);
  const url = companionUrl(tab, ports);

  const postTheme = useCallback(() => {
    const win = iframeRef.current?.contentWindow;
    if (win && url) win.postMessage({ type: "theme", theme }, new URL(url).origin);
  }, [theme, url]);

  useEffect(postTheme, [postTheme]);

  useEffect(() => {
    if (!url) {
      setState("no-port");
      return;
    }
    let cancelled = false;
    setState("connecting");
    fetch(`${url}api/health`, { mode: "no-cors", cache: "no-store" })
      .then(() => !cancelled && setState("up"))
      .catch(() => !cancelled && setState("down"));
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, retryTick]);

  if (state === "no-port") {
    return (
      <div className="p-6">
        <Card>
          <CardHeader>
            <CardTitle>{info.title}</CardTitle>
          </CardHeader>
          <CardContent className="italic text-text-secondary">The Part 1 backend did not report a port for this service.</CardContent>
        </Card>
      </div>
    );
  }

  if (state === "idle" || state === "connecting") {
    return (
      <div className="p-6">
        <Card>
          <CardContent className="flex items-center gap-2 text-text-secondary">
            <Spinner /> Connecting to {url}…
          </CardContent>
        </Card>
      </div>
    );
  }

  if (state === "down") {
    return (
      <div className="p-6">
        <Card>
          <CardHeader>
            <CardTitle>{info.title} is not running</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <p>
              Nothing answered at <code>{url}</code>. Start it with:
            </p>
            <pre className="rounded-xl bg-background-secondary-default p-3 font-mono text-body-2-regular">{info.compose}</pre>
            <p className="text-caption-1-regular text-text-secondary">
              Without Docker: <code>{info.local}</code>
            </p>
            <Button
              variant="secondary"
              size="small"
              leadingIcon={RiRefreshLine}
              onClick={() => setRetryTick((n) => n + 1)}
              className="self-start"
            >
              Try again
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const src = companionSrc(tab, url);
  return (
    <iframe
      ref={iframeRef}
      src={src}
      title={info.title}
      onLoad={postTheme}
      className="companion-frame block w-full border-0 bg-background-full"
    />
  );
}
