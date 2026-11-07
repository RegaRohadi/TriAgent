"use client";

import type { ReactNode, Ref } from "react";
import type { TextProps as AriaTextProps } from "react-aria-components";
import { Text as AriaText } from "react-aria-components";
import { cx } from "@/utils/cx";

export interface HintTextProps extends AriaTextProps {
  children: ReactNode;
  isInvalid?: boolean;
  ref?: Ref<HTMLElement>;
}

export function HintText({
  isInvalid = false,
  className,
  ...props
}: HintTextProps) {
  return (
    <AriaText
      slot={isInvalid ? "errorMessage" : "description"}
      {...props}
      className={cx(
        "pt-1 text-[11px] leading-relaxed text-ink-faint",
        isInvalid && "text-danger",
        className,
      )}
    />
  );
}
