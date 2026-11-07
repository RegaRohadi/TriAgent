export function EmptyState({ icon: Icon, title, description, action, className = "" }) {
  return (
    <div
      className={`flex flex-col items-center justify-center rounded-2xl border border-dashed border-line-strong bg-surface/60 px-6 py-10 text-center ${className}`}
    >
      {Icon ? (
        <span className="mb-3 grid size-11 place-items-center rounded-xl bg-surface-2 text-ink-faint">
          <Icon size={20} aria-hidden />
        </span>
      ) : null}
      {title ? <h3 className="text-sm font-semibold text-ink">{title}</h3> : null}
      {description ? (
        <p className="mt-1 max-w-md text-xs leading-relaxed text-ink-faint">{description}</p>
      ) : null}
      {action ? <div className="mt-4">{action}</div> : null}
    </div>
  );
}
