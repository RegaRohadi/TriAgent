export const MENU_POPOVER_SURFACE = [
  "max-w-[calc(100vw-32px)] overflow-y-auto",
  "rounded-xl border border-line bg-surface p-2 shadow-[var(--shadow-dropdown)]",
  "transition duration-150 ease-out",
  "data-[entering]:opacity-0 data-[entering]:scale-95 data-[entering]:blur-[2px]",
  "data-[exiting]:opacity-0 data-[exiting]:scale-95 data-[exiting]:blur-[2px]",
  "data-[placement=bottom]:origin-top-left data-[placement=top]:origin-bottom-left",
  "data-[placement=left]:origin-right data-[placement=right]:origin-left",
].join(" ");

export const MENU_POPOVER_WIDTH = "w-[266px]";

export const MENU_ITEMS_CONTAINER = "flex w-full flex-col gap-0.5 outline-none";

export const MENU_ITEM = [
  "flex w-full cursor-pointer items-center gap-2 rounded-lg p-2 text-left",
  "text-[13px] text-ink outline-none transition-colors",
].join(" ");

export const MENU_ITEM_ACTIVE = "bg-surface-2";

export const MENU_ITEM_INTERACTIVE =
  "hover:bg-surface-2 focus-visible:bg-surface-2";
