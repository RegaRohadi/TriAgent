import type { HTMLAttributes, Ref } from "react";
import { cx } from "@/utils/cx";

interface DivProps extends HTMLAttributes<HTMLDivElement> {
  ref?: Ref<HTMLDivElement>;
}

export function Card({ className, ref, ...props }: DivProps) {
  return (
    <div
      ref={ref}
      className={cx(
        "flex min-w-0 flex-col gap-3.5 rounded-[1.15rem] border border-line bg-surface p-4 shadow-card md:p-5",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ref, ...props }: DivProps) {
  return <div ref={ref} className={cx("flex flex-wrap items-center justify-between gap-3", className)} {...props} />;
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cx("text-[0.95rem] font-bold tracking-tight text-ink", className)} {...props} />;
}

export function CardContent({ className, ref, ...props }: DivProps) {
  return (
    <div ref={ref} className={cx("min-w-0 text-[13px] leading-relaxed text-ink-soft", className)} {...props} />
  );
}
