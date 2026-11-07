import type { HTMLAttributes, Ref } from "react";
import { cx, sortCx } from "@/utils/cx";

type ChipVariant = "bold" | "subtle" | "caption";
type ChipColor = "lime" | "rose" | "yellow" | "cyan" | "blue" | "purple" | "neutral" | "gray" | "soft";

export interface ChipProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: ChipVariant;
  color?: ChipColor;
  ref?: Ref<HTMLSpanElement>;
}

const styles = sortCx({
  base: "inline-flex items-center justify-center gap-1 rounded-full border px-2.5 whitespace-nowrap font-semibold leading-normal transition-[padding,font-size] duration-200 ease",
  variant: {
    bold: "py-0.5 text-[11px]",
    subtle: "py-1 text-[11px]",
    caption: "py-1 text-[10.5px]",
  },
  color: {
    lime: "border-success/25 bg-success-soft text-success",
    rose: "border-danger/25 bg-danger-soft text-danger",
    yellow: "border-accent/25 bg-accent-soft text-accent",
    cyan: "border-brand/25 bg-brand-soft text-brand",
    blue: "border-brand/25 bg-brand-soft text-brand",
    purple: "border-brand/25 bg-brand-soft text-brand",
    neutral: "border-line bg-surface-2 text-ink-soft",
    gray: "border-line bg-surface-2 text-ink-soft",
    soft: "border-line bg-surface text-ink-soft",
  },
});

export function Chip({
  variant = "bold",
  color = "neutral",
  className,
  ref,
  ...props
}: ChipProps) {
  return (
    <span
      ref={ref}
      className={cx(styles.base, styles.variant[variant], styles.color[color], className)}
      {...props}
    />
  );
}
