import { RiChat3Line, RiGlobalLine, RiMailLine, RiMoonLine, RiSunLine } from "@remixicon/react";
import { Button } from "@/components/base/buttons/button";
import { Tab, TabList, Tabs } from "@/components/base/tabs/tabs";

const TAB_LABEL = {
  part1: "Mail · email agent",
  part2: "Lens · scrape & summarize",
  part3: "Docs · document chat",
};

const TAB_ICON = {
  part1: RiMailLine,
  part2: RiGlobalLine,
  part3: RiChat3Line,
};

export function Header({ headerRef, tabs, tab, onSelectTab, meta, theme, onToggleTheme }) {
  const dark = theme === "dark";
  const toggleLabel = dark ? "Switch to light mode" : "Switch to dark mode";

  return (
    <header ref={headerRef} className="border-b border-separator-border bg-background-full px-6 pt-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
        <h1 className="text-title-3-semibold text-text-primary">TriAgent</h1>
        <span className="text-caption-1-regular text-text-secondary">
          Three agents · one shared core
        </span>
        <span className="text-caption-1-regular text-text-secondary" hidden={tab !== "part1"}>
          {meta}
        </span>
        <Button
          variant="secondary"
          size="small"
          iconOnly
          leadingIcon={dark ? RiSunLine : RiMoonLine}
          aria-label={toggleLabel}
          title={toggleLabel}
          onClick={onToggleTheme}
          className="ml-auto"
        />
      </div>
      <Tabs selectedKey={tab} onSelectionChange={onSelectTab} className="mt-2 gap-0">
        <TabList aria-label="TriAgent modules" className="overflow-x-auto border-b-0">
          {tabs.map((t) => (
            <Tab key={t} id={t} icon={TAB_ICON[t]}>
              {TAB_LABEL[t]}
            </Tab>
          ))}
        </TabList>
      </Tabs>
    </header>
  );
}
