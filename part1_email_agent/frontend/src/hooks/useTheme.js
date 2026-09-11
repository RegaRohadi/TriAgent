import { useEffect, useState } from "react";

const STORAGE_KEY = "theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

function storedTheme() {
  try {
    const t = localStorage.getItem(STORAGE_KEY);
    return t === "light" || t === "dark" ? t : null;
  } catch {
    return null;
  }
}

export function useTheme() {
  const [theme, setTheme] = useState(() => storedTheme() || (window.matchMedia(DARK_QUERY).matches ? "dark" : "light"));

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  useEffect(() => {
    const query = window.matchMedia(DARK_QUERY);
    const onChange = (e) => {
      if (!storedTheme()) setTheme(e.matches ? "dark" : "light");
    };
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  function toggleTheme() {
    const next = theme === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
    }
    setTheme(next);
  }

  return { theme, toggleTheme };
}
