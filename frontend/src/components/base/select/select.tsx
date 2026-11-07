"use client";

import { createContext, useContext, useRef, useState } from "react";
import type { ReactNode, Ref } from "react";
import {
  Button as AriaButton,
  ListBox as AriaListBox,
  ListBoxItem as AriaListBoxItem,
  Popover as AriaPopover,
  Select as AriaSelect,
  SelectValue as AriaSelectValue,
} from "react-aria-components";
import type {
  ListBoxItemProps as AriaListBoxItemProps,
  SelectProps as AriaSelectProps,
  SelectValueRenderProps as AriaSelectValueRenderProps,
} from "react-aria-components";
import {
  MENU_ITEM,
  MENU_ITEM_ACTIVE,
  MENU_ITEMS_CONTAINER,
  MENU_POPOVER_SURFACE,
  MENU_POPOVER_WIDTH,
} from "@/components/base/dropdown/menu-styles";
import { ChevronDownSmall } from "@/components/foundations/icons/chevrons";
import { cx } from "@/utils/cx";
import { useDismissOnOutsidePress, useTriggerToggle } from "@/utils/use-dismiss-on-outside-press";

export type SelectSize = "sm" | "md";

const SelectSizeContext = createContext<SelectSize>("md");

export interface SelectProps<T extends object>
  extends Omit<AriaSelectProps<T>, "children"> {
  className?: string;
  triggerClassName?: string;
  popoverClassName?: string;
  size?: SelectSize;
  children: ReactNode;
  items?: Iterable<T>;
  renderValue?: ReactNode | ((values: AriaSelectValueRenderProps<T>) => ReactNode);
  ref?: Ref<HTMLDivElement>;
}

export function Select<T extends object>({
  className,
  triggerClassName,
  popoverClassName,
  size = "md",
  children,
  items,
  renderValue,
  ref,
  ...props
}: SelectProps<T>) {
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLElement>(null);
  const [isOpen, setIsOpen] = useState(false);
  useDismissOnOutsidePress(isOpen, () => setIsOpen(false), [triggerRef, popoverRef]);
  const allowOpenChange = useTriggerToggle(isOpen, triggerRef);

  return (
    <AriaSelect
      ref={ref}
      {...props}
      isOpen={isOpen}
      onOpenChange={(o) => allowOpenChange(o) && setIsOpen(o)}
      className={cx("group flex flex-col", className)}
    >
      {({ isOpen }) => (
        <>
          <AriaButton
            ref={triggerRef}
            className={cx(
              "flex w-full cursor-pointer items-center justify-between rounded-[0.75rem]",
              "border border-line-strong bg-surface shadow-xs",
              "text-ink",
              "transition-[background-color,border-color,box-shadow,padding,font-size] duration-150 ease",
              "hover:border-ink-faint/60 hover:bg-surface-2",
              "outline-none focus-visible:border-brand focus-visible:ring-[3px] focus-visible:ring-brand/15",
              "disabled:cursor-not-allowed disabled:border-line disabled:bg-surface-2 disabled:text-ink-faint disabled:shadow-none",
              size === "sm"
                ? "gap-1 px-2.5 py-1.5 text-[11px]"
                : "gap-1.5 px-3 py-2.5 text-[13px]",
              triggerClassName,
            )}
          >
            <AriaSelectValue
              className={cx(
                "flex min-w-0 items-center truncate",
                size === "sm" ? "gap-1" : "gap-[5px]",
              )}
            >
              {renderValue as never}
            </AriaSelectValue>
            <ChevronDownSmall
              className={cx(
                "shrink-0 text-text-secondary transition-transform duration-200 ease",
                size === "sm" ? "size-3.5" : "size-4",
                isOpen && "rotate-180",
              )}
            />
          </AriaButton>
          <AriaPopover
            ref={popoverRef}
            isNonModal
            offset={4}
            className={cx(
              MENU_POPOVER_WIDTH,
              MENU_POPOVER_SURFACE,
              "p-2",
              popoverClassName,
            )}
          >
            <AriaListBox
              items={items}
              className={cx(MENU_ITEMS_CONTAINER, "max-h-[240px] overflow-auto")}
            >
              <SelectSizeContext.Provider value={size}>{children}</SelectSizeContext.Provider>
            </AriaListBox>
          </AriaPopover>
        </>
      )}
    </AriaSelect>
  );
}

export interface SelectItemProps extends Omit<AriaListBoxItemProps, "children"> {
  children?: ReactNode;
}

export function SelectItem({ className, children, ...props }: SelectItemProps) {
  const size = useContext(SelectSizeContext);
  return (
    <AriaListBoxItem
      {...props}
      className={(state) =>
        cx(
          MENU_ITEM,
          size === "sm" ? "px-2 py-1.5 text-body-2-medium" : "text-body-medium",
          (state.isFocused || state.isSelected) && MENU_ITEM_ACTIVE,
          state.isDisabled && "cursor-not-allowed text-text-disabled",
          typeof className === "function" ? className(state) : className,
        )
      }
    >
      {children}
    </AriaListBoxItem>
  );
}
