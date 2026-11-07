"use client";

import type { ReactNode, Ref } from "react";
import { TextArea as AriaTextArea, TextField as AriaTextField } from "react-aria-components";
import type { TextFieldProps as AriaTextFieldProps } from "react-aria-components";
import { Label } from "./label";
import { HintText } from "./hint-text";
import { cx } from "@/utils/cx";

export interface TextAreaProps extends Omit<AriaTextFieldProps, "className"> {
  label?: ReactNode;
  hint?: ReactNode;
  placeholder?: string;
  rows?: number;
  className?: string;
  textAreaClassName?: string;
  ref?: Ref<HTMLTextAreaElement>;
}

export function TextArea({
  label,
  hint,
  placeholder,
  rows = 4,
  className,
  textAreaClassName,
  ref,
  ...props
}: TextAreaProps) {
  return (
    <AriaTextField
      {...props}
      aria-label={props["aria-label"] ?? (!label && placeholder ? placeholder : undefined)}
      className={cx("group flex h-max w-full flex-col items-start gap-1", className)}
    >
      {({ isRequired, isInvalid }) => (
        <>
          {label && (
            <Label isRequired={isRequired} isInvalid={isInvalid}>
              {label}
            </Label>
          )}
          <AriaTextArea
            ref={ref}
            rows={rows}
            placeholder={placeholder}
            className={({ isHovered, isFocused, isDisabled, isInvalid: invalid }) =>
              cx(
                "w-full resize-y rounded-[0.75rem] border border-line-strong bg-surface px-3 py-2.5",
                "font-sans text-[13px] leading-relaxed text-ink outline-none",
                "ring-0 ring-transparent placeholder:text-ink-faint",
                "transition-[background-color,border-color,box-shadow] duration-[var(--input-transition-ms)] ease",
                isHovered && !isFocused && !isDisabled && !invalid && "border-ink-faint/60",
                isFocused && !isDisabled && !invalid && "border-brand ring-[3px] ring-brand/15",
                isDisabled && "cursor-not-allowed bg-surface-2 text-ink-faint",
                invalid && "border-danger bg-danger-soft",
                textAreaClassName,
              )
            }
          />
          {hint && <HintText isInvalid={isInvalid}>{hint}</HintText>}
        </>
      )}
    </AriaTextField>
  );
}
