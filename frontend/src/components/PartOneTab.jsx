import { useEffect } from "react";
import { useBackendMeta } from "../hooks/useBackendMeta.js";
import { useTicketHistory } from "../hooks/useTicketHistory.js";
import { useOutPanel } from "../hooks/useOutPanel.js";
import { useFetchInbox } from "../hooks/useFetchInbox.js";
import { PartOnePanel } from "./PartOnePanel.jsx";

export function PartOneTab({ active, onMeta }) {
  const { meta, samples } = useBackendMeta();
  const history = useTicketHistory();
  const { out, setOut, runProcess, running, openTicket } = useOutPanel(history.loadHistory);
  const fetchInbox = useFetchInbox(setOut, history.loadHistory);

  useEffect(() => {
    onMeta(meta);
  }, [meta, onMeta]);

  return (
    <PartOnePanel
      active={active}
      samples={samples}
      onRun={runProcess}
      running={running}
      history={history}
      fetchInbox={fetchInbox}
      out={out}
      onOpenTicket={openTicket}
    />
  );
}
