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
                "w-full resize-y rounded-2lg border-0 bg-background-tertiary-default px-3 py-2",
                "font-sans text-body-regular text-text-primary outline-none",
                "ring-2 ring-inset ring-transparent placeholder:text-text-tertiary",
                "transition-[background-color,box-shadow] duration-[var(--input-transition-ms)] ease",
                isHovered && !isFocused && !isDisabled && !invalid && "ring-border-button-hover",
                isFocused && !isDisabled && !invalid && "ring-border-button-active",
                isDisabled && "cursor-not-allowed bg-input-disabled-background text-input-disabled-text",
                invalid && "bg-background-tertiary-error",
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
