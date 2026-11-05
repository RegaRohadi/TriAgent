import { useEffect, useRef, useState } from "react";
import { DEFAULT_TAB, PORTS } from "../backend.js";
import { TABS, validTab } from "../constants.js";

export function useTabs() {
  const [tab, setTab] = useState(() =>
    validTab(location.hash.slice(1), validTab(DEFAULT_TAB, "part1")),
  );
  const headerRef = useRef(null);

  useEffect(() => {
    const hash = `#${tab}`;
    if (location.hash !== hash) history.replaceState(null, "", `${location.pathname}${location.search}${hash}`);
  }, [tab]);

  useEffect(() => {
    const onHashChange = () => setTab(validTab(location.hash.slice(1), DEFAULT_TAB));
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

  return { tab, setTab, tabs: TABS, ports: PORTS, headerRef };
}
