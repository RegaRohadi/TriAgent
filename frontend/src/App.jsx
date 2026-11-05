import { useEffect, useState } from "react";
import { useTabs } from "./hooks/useTabs.js";
import { useTheme } from "./hooks/useTheme.js";
import { Header } from "./components/Header.jsx";
import { PartOneTab } from "./components/PartOneTab.jsx";
import { PartTwoPanel } from "./components/PartTwoPanel.jsx";
import { PartThreePanel } from "./components/PartThreePanel.jsx";

export default function App() {
  const { theme, toggleTheme } = useTheme();
  const { tab, setTab, tabs, headerRef } = useTabs();
  const [meta, setMeta] = useState("loading…");

  const [visited, setVisited] = useState(() => new Set([tab]));
  useEffect(() => {
    setVisited((prev) => (prev.has(tab) ? prev : new Set(prev).add(tab)));
  }, [tab]);

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

      {visited.has("part1") && <PartOneTab active={tab === "part1"} onMeta={setMeta} />}
      {visited.has("part2") && <PartTwoPanel active={tab === "part2"} />}
      {visited.has("part3") && <PartThreePanel active={tab === "part3"} />}
    </>
  );
}
