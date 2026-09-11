import { useBackendMeta } from "./hooks/useBackendMeta.js";
import { useTicketHistory } from "./hooks/useTicketHistory.js";
import { useOutPanel } from "./hooks/useOutPanel.js";
import { useFetchInbox } from "./hooks/useFetchInbox.js";
import { useTabs } from "./hooks/useTabs.js";
import { useTheme } from "./hooks/useTheme.js";
import { Header } from "./components/Header.jsx";
import { PartOnePanel } from "./components/PartOnePanel.jsx";
import { CompanionTab } from "./components/CompanionTab.jsx";

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const { tab, setTab, tabs, visitedCompanions, headerRef } = useTabs();
  const { meta, companionPorts, samples } = useBackendMeta();
  const history = useTicketHistory();
  const { out, setOut, runProcess, running, openTicket } = useOutPanel(history.loadHistory);
  const fetchInbox = useFetchInbox(setOut, history.loadHistory);

  return (
    <>
      <Header
        headerRef={headerRef}
        tabs={tabs}
        tab={tab}
        onSelectTab={setTab}
        meta={meta}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <PartOnePanel
        active={tab === "part1"}
        samples={samples}
        onRun={runProcess}
        running={running}
        history={history}
        fetchInbox={fetchInbox}
        out={out}
        onOpenTicket={openTicket}
      />

      {tabs
        .filter((t) => t !== "part1")
        .map((t) => (
          <CompanionTab
            key={t}
            tab={t}
            active={tab === t}
            visited={visitedCompanions.has(t)}
            ports={companionPorts}
            theme={theme}
          />
        ))}
    </>
  );
}
