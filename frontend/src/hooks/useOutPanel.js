import { useEffect, useState } from "react";
import { api } from "../api.js";

export function useOutPanel(loadHistory) {
  const [out, setOut] = useState(null);
  const [running, setRunning] = useState(false);

  async function runProcess(payload) {
    setRunning(true);
    setOut({ kind: "processing" });
    try {
      const result = await api.process(payload);
      setOut({ kind: "result", state: result });
      loadHistory();
    } catch (err) {
      setOut({ kind: "error", message: err.message });
    } finally {
      setRunning(false);
    }
  }

  async function openTicket(traceId) {
    try {
      const t = await api.ticket(traceId);
      setOut({ kind: "ticket", ticket: t });
      loadHistory(t.trace_id);
    } catch (err) {
      setOut({ kind: "error", message: err.message });
    }
  }

  useEffect(() => {
    const wanted = new URLSearchParams(location.search).get("ticket");
    if (wanted) openTicket(wanted);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { out, setOut, runProcess, running, openTicket };
}
