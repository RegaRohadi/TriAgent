import { cx } from "@/utils/cx";

export function RowButton({ selected = false, disabled = false, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-current={selected || undefined}
      className={cx(
        "block w-full min-w-0 rounded-xl border px-3 py-2.5 text-left outline-none transition-colors duration-150",
        "focus-visible:ring-2 focus-visible:ring-brand/35",
        "disabled:cursor-not-allowed disabled:opacity-60",
        selected
          ? "border-brand/60 bg-brand-soft"
          : "cursor-pointer border-line bg-surface enabled:hover:border-line-strong enabled:hover:bg-surface-2",
      )}
    >
      {children}
    </button>
  );
}
