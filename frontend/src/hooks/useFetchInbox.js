import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";
import { FETCH_POLL_MS } from "../constants.js";

export function useFetchInbox(setOut, loadHistory) {
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null);
  const pollTimer = useRef(null);

  useEffect(() => () => clearTimeout(pollTimer.current), []);

  async function fetchNow() {
    setBusy(true);
    setStatus({ kind: "note", text: "Reading inbox…" });
    try {
      let job = await api.fetchNow();
      if (!job.total) {
        setStatus({ kind: "note", text: "Inbox is empty." });
        return;
      }
      setOut({ kind: "fetch", job });

      while (!job.finished) {
        await new Promise((resolve) => (pollTimer.current = setTimeout(resolve, FETCH_POLL_MS)));
        job = await api.fetchStatus(job.job_id);
        setOut({ kind: "fetch", job });
        setStatus({ kind: "note", text: `Classifying… ${job.total - job.pending}/${job.total}` });
      }

      const processed = job.messages.filter((m) => m.status === "done").length;
      setStatus(
        processed
          ? { kind: "ok", text: `${processed} new email(s) processed (${job.total} in inbox).` }
          : { kind: "note", text: `No new mail — all ${job.total} message(s) already processed.` }
      );
      await loadHistory();
    } catch (err) {
      setStatus({ kind: "err", text: err.message });
    } finally {
      setBusy(false);
    }
  }

  return { busy, status, fetchNow };
}
