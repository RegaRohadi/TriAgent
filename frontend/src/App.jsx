import { useEffect, useState } from "react";
import { useTabs } from "./hooks/useTabs.js";
import { useTheme } from "./hooks/useTheme.js";
import { AppShell } from "./components/AppShell.jsx";
import { PartOneTab } from "./components/PartOneTab.jsx";
import { PartTwoPanel } from "./components/PartTwoPanel.jsx";
import { PartThreePanel } from "./components/PartThreePanel.jsx";

const TITLES = {
  part1: "Mail · TriAgent",
  part2: "Lens · TriAgent",
  part3: "Docs · TriAgent",
};

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const { tab, setTab } = useTabs();

  const [visited, setVisited] = useState(() => new Set([tab]));
  useEffect(() => {
    setVisited((prev) => (prev.has(tab) ? prev : new Set(prev).add(tab)));
    document.title = TITLES[tab] || "TriAgent";
  }, [tab]);

  const selectTab = (next) => {
    if (next !== tab) setTab(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <AppShell
      tab={tab}
      onSelectTab={selectTab}
      theme={theme}
      onToggleTheme={toggleTheme}
    >
      {visited.has("part1") && <PartOneTab active={tab === "part1"} />}
      {visited.has("part2") && <PartTwoPanel active={tab === "part2"} />}
      {visited.has("part3") && <PartThreePanel active={tab === "part3"} />}
    </AppShell>
  );
}
