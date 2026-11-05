import { useCallback, useEffect, useState } from "react";
import { api } from "../api.js";

export function useTicketHistory() {
  const [historyData, setHistoryData] = useState(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [selectedTrace, setSelectedTrace] = useState(null);

  const loadHistory = useCallback(async (keepSelection, filterOverride) => {
    try {
      const data = await api.tickets(filterOverride ?? statusFilter);
      setHistoryData(data);
      if (keepSelection !== undefined) setSelectedTrace(keepSelection);
    } catch {
      setHistoryData((current) => current ?? { counts: {}, tickets: [] });
    }
  }, [statusFilter]);

  useEffect(() => {
    loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loadHistory]);

  function changeFilter(value) {
    setStatusFilter(value);
    loadHistory(undefined, value);
  }

  return { historyData, statusFilter, changeFilter, selectedTrace, setSelectedTrace, loadHistory };
}
