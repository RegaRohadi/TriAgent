"use client";

import {
  createContext,
  useContext,
  type ComponentType,
  type ReactNode,
  type Ref,
} from "react";
import {
  Group as AriaGroup,
  Input as AriaInput,
  TextField as AriaTextField,
} from "react-aria-components";
import type {
  InputProps as AriaInputProps,
  TextFieldProps as AriaTextFieldProps,
} from "react-aria-components";
import { Label } from "./label";
import { HintText } from "./hint-text";
import { cx, sortCx } from "@/utils/cx";

type InputSize = "medium" | "small";

type IconComponent = ComponentType<{
  className?: string;
  "aria-hidden"?: boolean | "true" | "false";
}>;

interface TextFieldContextValue {
  size?: InputSize;
  fieldClassName?: string;
  inputClassName?: string;
}

const TextFieldContext = createContext<TextFieldContextValue>({});

export interface TextFieldProps
  extends Omit<AriaTextFieldProps, "className">,
    TextFieldContextValue {
  className?: string;
  children?: ReactNode | ((state: { isRequired: boolean; isInvalid: boolean; isDisabled: boolean; isReadOnly: boolean }) => ReactNode);
}

export function TextField({
  size = "medium",
  fieldClassName,
  inputClassName,
  className,
  children,
  ...props
}: TextFieldProps) {
  return (
    <TextFieldContext.Provider value={{ size, fieldClassName, inputClassName }}>
      <AriaTextField
        {...props}
        data-input-size={size}
        className={cx(
          "group flex h-max w-full flex-col items-start gap-1",
          className,
        )}
      >
        {children as never}
      </AriaTextField>
    </TextFieldContext.Provider>
  );
}

TextField.displayName = "TextField";

export interface InputBaseProps extends Omit<AriaInputProps, "size" | "className"> {
  size?: InputSize;
  className?: string;
  leadingIcon?: IconComponent;
  trailingIcon?: IconComponent;
  leadingAddon?: ReactNode;
  fieldClassName?: string;
  ref?: Ref<HTMLInputElement>;
  groupRef?: Ref<HTMLDivElement>;
}

const inputStyles = sortCx({
  field: [
    "relative flex w-full items-center",
    "rounded-[0.75rem]",
    "border border-line-strong bg-surface text-ink-faint",
    "ring-0 ring-transparent",
    "transition-[background-color,border-color,box-shadow,color] duration-[var(--input-transition-ms)] ease",
  ].join(" "),

  fieldSize: {
    medium: "h-10 px-3",
    small: "h-8 px-2.5",
  },

  fieldWithAddonSize: {
    medium: "h-10 pl-2 pr-3",
    small: "h-8 pl-1.5 pr-2.5",
  },

  content: "flex w-full items-center gap-2 min-w-0",
  leftSection: "flex flex-1 items-center gap-2 min-w-0",

  input: [
    "min-w-0 flex-1 bg-transparent border-0 outline-none p-0 m-0",
    "font-sans text-[13px] text-ink",
    "placeholder:text-ink-faint",
    "focus:placeholder:text-ink-faint",
    "disabled:text-ink-faint disabled:placeholder:text-ink-faint",
    "disabled:cursor-not-allowed",
    "aria-invalid:placeholder:text-danger/70",
  ].join(" "),

  icon: "size-4 shrink-0 text-ink-faint",
});

export function InputBase({
  size: sizeProp,
  leadingIcon: Leading,
  trailingIcon: Trailing,
  leadingAddon,
  fieldClassName,
  className,
  ref,
  groupRef,
  ...inputProps
}: InputBaseProps) {
  const ctx = useContext(TextFieldContext);
  const size: InputSize = sizeProp ?? ctx.size ?? "medium";
  const hasAddon = leadingAddon !== undefined && leadingAddon !== null;

  return (
    <AriaGroup
      ref={groupRef}
      className={({ isFocusWithin, isHovered, isDisabled, isInvalid }) =>
        cx(
          inputStyles.field,
          hasAddon
            ? inputStyles.fieldWithAddonSize[size]
            : inputStyles.fieldSize[size],
          isHovered &&
            !isFocusWithin &&
            !isDisabled &&
            !isInvalid &&
            "border-ink-faint/60",
          isFocusWithin &&
            !isDisabled &&
            !isInvalid &&
            "border-brand ring-[3px] ring-brand/15",
          isDisabled &&
            "bg-surface-2 text-ink-faint",
          isInvalid && "border-danger bg-danger-soft text-danger",
          ctx.fieldClassName,
          fieldClassName,
        )
      }
    >
      <div className={inputStyles.content}>
        <div className={inputStyles.leftSection}>
          {hasAddon ? (
            leadingAddon
          ) : Leading ? (
            <Leading className={inputStyles.icon} aria-hidden />
          ) : null}
          <AriaInput
            ref={ref}
            {...inputProps}
            className={cx(inputStyles.input, ctx.inputClassName, className)}
          />
        </div>
        {Trailing ? (
          <Trailing className={inputStyles.icon} aria-hidden />
        ) : null}
      </div>
    </AriaGroup>
  );
}

InputBase.displayName = "InputBase";

export interface InputProps
  extends Omit<TextFieldProps, "children">,
    Pick<
      InputBaseProps,
      | "leadingIcon"
      | "trailingIcon"
      | "leadingAddon"
      | "fieldClassName"
      | "groupRef"
      | "ref"
    > {
  label?: ReactNode;
  hint?: ReactNode;
  tooltip?: boolean | string;
  placeholder?: string;
}

export function Input({
  label,
  hint,
  tooltip,
  placeholder,
  leadingIcon,
  trailingIcon,
  leadingAddon,
  fieldClassName,
  ref,
  groupRef,
  className,
  ...textFieldProps
}: InputProps) {
  return (
    <TextField
      {...textFieldProps}
      className={className}
      aria-label={
        textFieldProps["aria-label"] ??
        (!label && typeof placeholder === "string" ? placeholder : undefined)
      }
    >
      {({ isRequired, isInvalid }) => (
        <>
          {label && (
            <Label
              isRequired={isRequired}
              isInvalid={isInvalid}
              tooltip={tooltip}
            >
              {label}
            </Label>
          )}
          <InputBase
            ref={ref}
            groupRef={groupRef}
            placeholder={placeholder}
            leadingIcon={leadingIcon}
            trailingIcon={trailingIcon}
            leadingAddon={leadingAddon}
            fieldClassName={fieldClassName}
          />
          {hint && <HintText isInvalid={isInvalid}>{hint}</HintText>}
        </>
      )}
    </TextField>
  );
}

Input.displayName = "Input";
