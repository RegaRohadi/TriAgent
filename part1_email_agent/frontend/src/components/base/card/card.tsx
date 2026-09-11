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
        "flex min-w-0 flex-col gap-4 rounded-3xl border border-border-button-default bg-background-full p-5 shadow-card",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ref, ...props }: DivProps) {
  return <div ref={ref} className={cx("flex items-center justify-between gap-3", className)} {...props} />;
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cx("text-headline-semibold text-text-primary", className)} {...props} />;
}

export function CardContent({ className, ref, ...props }: DivProps) {
  return <div ref={ref} className={cx("min-w-0 text-body-regular text-text-primary", className)} {...props} />;
}
