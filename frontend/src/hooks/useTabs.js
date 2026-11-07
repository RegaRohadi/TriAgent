import { useEffect, useState } from "react";
import { DEFAULT_TAB } from "../backend.js";
import { validTab } from "../constants.js";

export function useTabs() {
  const [tab, setTab] = useState(() =>
    validTab(location.hash.slice(1), validTab(DEFAULT_TAB, "part1")),
  );

  useEffect(() => {
    const hash = `#${tab}`;
    if (location.hash !== hash) history.replaceState(null, "", `${location.pathname}${location.search}${hash}`);
  }, [tab]);

  useEffect(() => {
    const onHashChange = () => setTab(validTab(location.hash.slice(1), DEFAULT_TAB));
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  return { tab, setTab };
}
