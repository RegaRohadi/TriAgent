import { useEffect, useState } from "react";
import {
  RiChat3Line,
  RiCloseLine,
  RiGlobalLine,
  RiMailLine,
  RiMenuLine,
  RiMoonLine,
  RiShieldCheckLine,
  RiSunLine,
} from "@remixicon/react";

const NAV = [
  {
    group: "Agents",
    items: [
      { id: "part1", label: "Mail", hint: "triage", icon: RiMailLine },
      { id: "part2", label: "Lens", hint: "read", icon: RiGlobalLine },
      { id: "part3", label: "Docs", hint: "ask", icon: RiChat3Line },
    ],
  },
];

function Logo({ onSelect }) {
  return (
    <button
      type="button"
      onClick={() => onSelect("part1")}
      className="flex cursor-pointer items-center gap-2.5 rounded-xl text-left outline-none transition-opacity hover:opacity-90 focus-visible:ring-2 focus-visible:ring-brand/40"
      aria-label="TriAgent — go to Mail"
    >
      <span className="grid size-9 shrink-0 place-items-center rounded-[11px] bg-[#0c1a2a] ring-1 ring-white/10">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
          <rect x="3" y="11" width="3.4" height="6" rx="1.1" fill="#5b9bf3" />
          <rect x="8.3" y="7" width="3.4" height="10" rx="1.1" fill="#a9cbfa" />
          <rect x="13.6" y="3" width="3.4" height="14" rx="1.1" fill="#eeb05a" />
        </svg>
      </span>
      <span className="leading-none">
        <span className="block text-[15px] font-extrabold tracking-tight text-ink">TriAgent.</span>
        <span className="mt-1 block text-[9px] font-semibold tracking-[0.16em] text-ink-faint uppercase">
          Three agents · one core
        </span>
      </span>
    </button>
  );
}

function SidebarNav({ tab, onSelect }) {
  return (
    <nav className="flex flex-col gap-6">
      {NAV.map((group) => (
        <div key={group.group}>
          <p className="mb-2 px-3 text-[10px] font-bold tracking-[0.16em] text-ink-faint uppercase">
            {group.group}
          </p>
          <ul className="space-y-1">
            {group.items.map((item) => {
              const active = tab === item.id;
              const Icon = item.icon;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(item.id)}
                    aria-current={active ? "page" : undefined}
                    className={`group flex w-full cursor-pointer items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors outline-none focus-visible:ring-2 focus-visible:ring-brand/40 ${
                      active
                        ? "bg-brand-soft text-brand"
                        : "text-ink-soft hover:bg-surface-2 hover:text-ink"
                    }`}
                  >
                    <Icon size={17} className={active ? "text-brand" : "text-ink-faint"} aria-hidden />
                    <span className="flex-1 text-left">{item.label}</span>
                    <span
                      className={`rounded-md px-1.5 py-0.5 text-[10px] font-semibold ${
                        active
                          ? "bg-surface/70 text-brand"
                          : "bg-surface-2 text-ink-faint group-hover:bg-surface-3"
                      }`}
                    >
                      {item.hint}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function SidebarNote() {
  return (
    <div className="rounded-xl border border-line bg-surface-2 p-3.5">
      <div className="flex items-center gap-2 text-[10px] font-bold tracking-wide text-ink-faint uppercase">
        <RiShieldCheckLine size={13} aria-hidden /> Local demo
      </div>
      <p className="mt-1.5 text-[11px] leading-relaxed text-ink-soft">
        This UI talks to three local services. Start them with{" "}
        <code className="rounded bg-surface px-1 py-0.5 font-mono text-[10px] whitespace-nowrap text-ink">docker compose up -d</code>.
      </p>
    </div>
  );
}

function ThemeButton({ theme, onToggle, className = "" }) {
  const dark = theme === "dark";
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
      className={`flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-2 text-xs font-medium text-ink-soft transition-colors outline-none hover:bg-surface-2 hover:text-ink focus-visible:ring-2 focus-visible:ring-brand/40 ${className}`}
    >
      {dark ? <RiSunLine size={15} aria-hidden /> : <RiMoonLine size={15} aria-hidden />}
      <span>{dark ? "Light mode" : "Dark mode"}</span>
    </button>
  );
}

export function AppShell({ tab, onSelectTab, theme, onToggleTheme, children }) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return undefined;
    const onKey = (event) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const select = (id) => {
    onSelectTab(id);
    setOpen(false);
  };

  return (
    <div className="min-h-dvh">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[252px] flex-col border-r border-line bg-surface px-4 py-5 lg:flex">
        <div className="px-2">
          <Logo onSelect={select} />
        </div>
        <div className="mt-8 flex-1 overflow-y-auto">
          <SidebarNav tab={tab} onSelect={select} />
        </div>

        <div className="mt-4">
          <SidebarNote />
        </div>

        <div className="mt-3 flex items-center justify-between gap-2">
          <ThemeButton theme={theme} onToggle={onToggleTheme} className="flex-1" />
          <span className="text-[10px] font-medium text-ink-faint">v1.0</span>
        </div>
      </aside>

      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-surface/90 px-4 backdrop-blur lg:hidden">
        <Logo onSelect={select} />
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onToggleTheme}
            aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
            className="grid size-9 cursor-pointer place-items-center rounded-lg text-ink-soft transition-colors outline-none hover:bg-surface-2 hover:text-ink focus-visible:ring-2 focus-visible:ring-brand/40"
          >
            {theme === "dark" ? <RiSunLine size={17} aria-hidden /> : <RiMoonLine size={17} aria-hidden />}
          </button>
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            className="grid size-9 cursor-pointer place-items-center rounded-lg text-ink-soft transition-colors outline-none hover:bg-surface-2 hover:text-ink focus-visible:ring-2 focus-visible:ring-brand/40"
            aria-label={open ? "Close menu" : "Open menu"}
            aria-expanded={open}
            aria-controls="mobile-navigation"
          >
            {open ? <RiCloseLine size={19} aria-hidden /> : <RiMenuLine size={19} aria-hidden />}
          </button>
        </div>
      </header>

      {open ? (
        <div className="fixed inset-0 z-20 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 cursor-default bg-ink/30 backdrop-blur-sm"
            aria-label="Close menu"
            onClick={() => setOpen(false)}
          />
          <div
            id="mobile-navigation"
            className="fade-in absolute inset-x-3 top-14 max-h-[calc(100dvh-4.5rem)] overflow-y-auto rounded-2xl border border-line bg-surface p-4 shadow-[var(--shadow-pop)]"
          >
            <SidebarNav tab={tab} onSelect={select} />
            <div className="mt-5 border-t border-line pt-3">
              <SidebarNote />
              <ThemeButton theme={theme} onToggle={onToggleTheme} className="mt-2 w-full" />
            </div>
          </div>
        </div>
      ) : null}

      <main className="lg:pl-[252px]">
        <div className="container-page py-6 md:py-8">{children}</div>
        <footer className="container-page border-t border-line py-6 text-[11px] leading-relaxed text-ink-faint">
          <p>
            <span className="font-semibold text-ink-soft">TriAgent</span> — three agents sharing one core:
            triage, retrieval, and guardrails. Local demo, not a production support desk.
          </p>
        </footer>
      </main>
    </div>
  );
}
