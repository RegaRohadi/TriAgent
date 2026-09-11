import { useEffect, useRef, useState } from "react";
import { TABS, validTab } from "../constants.js";

export function useTabs() {
  const [tab, setTab] = useState(validTab(location.hash.slice(1)));
  const [visitedCompanions, setVisitedCompanions] = useState(new Set());
  const headerRef = useRef(null);

  useEffect(() => {
    if (tab !== "part1" && !visitedCompanions.has(tab)) {
      setVisitedCompanions((prev) => new Set(prev).add(tab));
    }
    const hash = `#${tab}`;
    if (location.hash !== hash) history.replaceState(null, "", `${location.pathname}${location.search}${hash}`);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  useEffect(() => {
    const onHashChange = () => setTab(validTab(location.hash.slice(1)));
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    function syncHeaderHeight() {
      if (headerRef.current) {
        document.documentElement.style.setProperty("--header-h", `${headerRef.current.offsetHeight}px`);
      }
    }
    syncHeaderHeight();
    window.addEventListener("resize", syncHeaderHeight);
    return () => window.removeEventListener("resize", syncHeaderHeight);
  }, [tab]);

  return { tab, setTab, tabs: TABS, visitedCompanions, headerRef };
}
