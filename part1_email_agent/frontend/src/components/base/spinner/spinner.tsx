import { RiLoader4Line } from "@remixicon/react";
import { cx } from "@/utils/cx";

export function Spinner({ className }: { className?: string }) {
  return <RiLoader4Line aria-hidden className={cx("size-4 shrink-0 animate-spin", className)} />;
}
