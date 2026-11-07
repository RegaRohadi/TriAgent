const TONE_STYLES = {
  neutral: "border-line bg-surface-2 text-ink-soft",
  brand: "border-brand/25 bg-brand-soft text-brand",
  success: "border-success/25 bg-success-soft text-success",
  danger: "border-danger/25 bg-danger-soft text-danger",
  accent: "border-accent/25 bg-accent-soft text-accent",
};

const DOT_STYLES = {
  neutral: "bg-ink-faint",
  brand: "bg-brand",
  success: "bg-success",
  danger: "bg-danger",
  accent: "bg-accent",
};

export function StatusBadge({ tone = "neutral", children, dot = true, className = "" }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold whitespace-nowrap ${TONE_STYLES[tone]} ${className}`}
    >
      {dot ? <span className={`size-1.5 rounded-full ${DOT_STYLES[tone]}`} aria-hidden /> : null}
      {children}
    </span>
  );
}

export function PageHeader({ eyebrow, title, description, meta, actions }) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-3xl">
        {eyebrow ? (
          <p className="text-[11px] font-bold tracking-[0.16em] text-brand uppercase">{eyebrow}</p>
        ) : null}
        <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-ink md:text-[1.75rem]">{title}</h1>
        {description ? (
          <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-ink-soft">{description}</p>
        ) : null}
        {meta ? <p className="mt-2 text-[11px] leading-relaxed text-ink-faint">{meta}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
    </header>
  );
}
