import { cx } from "@/utils/cx";

export function RowButton({ selected = false, disabled = false, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-current={selected || undefined}
      className={cx(
        "block w-full min-w-0 rounded-2xl border px-3 py-2.5 text-left outline-none transition-colors duration-150",
        "focus-visible:ring-2 focus-visible:ring-border-focus-ring",
        "disabled:cursor-not-allowed disabled:opacity-60",
        selected
          ? "border-accent-500 bg-pill-tab-blue-selected-background"
          : "cursor-pointer border-border-button-default enabled:hover:border-border-button-hover enabled:hover:bg-background-primary-hover"
      )}
    >
      {children}
    </button>
  );
}
