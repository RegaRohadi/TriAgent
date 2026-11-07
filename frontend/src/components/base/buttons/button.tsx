import type {
  AnchorHTMLAttributes,
  ButtonHTMLAttributes,
  ComponentType,
  ReactNode,
  Ref,
} from "react";
import { cx, sortCx } from "@/utils/cx";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "medium" | "small" | "xs";

type IconComponent = ComponentType<{
  className?: string;
  "aria-hidden"?: boolean | "true" | "false";
}>;

export interface ButtonProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  iconOnly?: boolean;
  leadingIcon?: IconComponent;
  trailingIcon?: IconComponent;
  children?: ReactNode;
  ref?: Ref<HTMLButtonElement>;
}

export interface ButtonLinkProps
  extends Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "children"> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  iconOnly?: boolean;
  leadingIcon?: IconComponent;
  trailingIcon?: IconComponent;
  children?: ReactNode;
  ref?: Ref<HTMLAnchorElement>;
}

const styles = sortCx({
  base: [
    "inline-flex items-center justify-center gap-2 whitespace-nowrap overflow-hidden",
    "font-sans font-semibold select-none cursor-pointer",
    "outline-none transition-[background-color,border-color,color,box-shadow,transform] duration-150 ease",
    "active:translate-y-px",
    "focus-visible:ring-2 focus-visible:ring-brand/35 focus-visible:ring-offset-2 focus-visible:ring-offset-paper",
    "disabled:cursor-not-allowed disabled:translate-y-0 disabled:opacity-50",
    "aria-disabled:cursor-not-allowed aria-disabled:translate-y-0 aria-disabled:opacity-50",
  ].join(" "),

  size: {
    medium: "h-10 rounded-[0.8rem] px-3.5 text-[13px]",
    small: "h-8 rounded-[0.65rem] px-3 text-[12px]",
    xs: "h-7 rounded-md px-2.5 text-[11px]",
  },

  iconOnlySize: {
    medium: "size-10 p-0",
    small: "size-8 p-0",
    xs: "size-7 p-0",
  },

  icon: {
    medium: "size-[17px] shrink-0",
    small: "size-[15px] shrink-0",
    xs: "size-[13px] shrink-0",
  },

  label: {
    medium: "inline-flex items-center justify-center shrink-0",
    small: "inline-flex items-center justify-center shrink-0",
    xs: "inline-flex items-center justify-center shrink-0",
  },

  variant: {
    primary: [
      "border border-brand-strong/15 bg-brand text-white shadow-xs",
      "hover:bg-brand-hover active:bg-brand-strong",
      "disabled:bg-surface-3 disabled:text-ink-faint disabled:border-line disabled:shadow-none",
      "aria-disabled:bg-surface-3 aria-disabled:text-ink-faint aria-disabled:border-line aria-disabled:shadow-none",
    ].join(" "),
    danger: [
      "border border-transparent bg-danger text-white shadow-xs",
      "hover:bg-danger/90 active:bg-danger",
      "disabled:bg-surface-3 disabled:text-ink-faint disabled:shadow-none",
      "aria-disabled:bg-surface-3 aria-disabled:text-ink-faint aria-disabled:shadow-none",
    ].join(" "),
    secondary: [
      "border border-line-strong bg-surface text-ink shadow-xs",
      "hover:border-line-strong hover:bg-surface-2 active:bg-surface-3",
      "disabled:bg-surface-2 disabled:border-line disabled:text-ink-faint disabled:shadow-none",
      "aria-disabled:bg-surface-2 aria-disabled:border-line aria-disabled:text-ink-faint aria-disabled:shadow-none",
    ].join(" "),
    ghost: [
      "bg-transparent text-ink-soft",
      "hover:bg-surface-2 hover:text-ink active:bg-surface-3",
      "disabled:bg-transparent disabled:text-ink-faint disabled:shadow-none",
      "aria-disabled:bg-transparent aria-disabled:text-ink-faint aria-disabled:shadow-none",
    ].join(" "),
  },
});

export function Button({
  variant = "primary",
  size = "medium",
  iconOnly = false,
  leadingIcon: Leading,
  trailingIcon: Trailing,
  children,
  className,
  type = "button",
  ref,
  ...props
}: ButtonProps) {
  return (
    <button
      ref={ref}
      type={type}
      className={cx(
        styles.base,
        styles.size[size],
        styles.variant[variant],
        iconOnly && styles.iconOnlySize[size],
        className,
      )}
      {...props}
    >
      {Leading ? <Leading className={styles.icon[size]} aria-hidden /> : null}
      {!iconOnly && children !== undefined && children !== null && (
        <span className={styles.label[size]}>{children}</span>
      )}
      {!iconOnly && Trailing ? (
        <Trailing className={styles.icon[size]} aria-hidden />
      ) : null}
    </button>
  );
}

export function ButtonLink({
  variant = "primary",
  size = "medium",
  iconOnly = false,
  leadingIcon: Leading,
  trailingIcon: Trailing,
  children,
  className,
  ref,
  ...props
}: ButtonLinkProps) {
  return (
    <a
      ref={ref}
      className={cx(
        styles.base,
        styles.size[size],
        styles.variant[variant],
        iconOnly && styles.iconOnlySize[size],
        className,
      )}
      {...props}
    >
      {Leading ? <Leading className={styles.icon[size]} aria-hidden /> : null}
      {!iconOnly && children !== undefined && children !== null && (
        <span className={styles.label[size]}>{children}</span>
      )}
      {!iconOnly && Trailing ? (
        <Trailing className={styles.icon[size]} aria-hidden />
      ) : null}
    </a>
  );
}

export const buttonStyles = styles;
