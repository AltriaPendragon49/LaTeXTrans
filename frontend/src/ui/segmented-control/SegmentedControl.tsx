import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

interface SegmentedControlItem<T extends string> {
  value: T
  label: ReactNode
  icon?: ReactNode
  disabled?: boolean
  testId?: string
}

interface SegmentedControlProps<T extends string> {
  value: T
  items: SegmentedControlItem<T>[]
  onValueChange: (value: T) => void
  className?: string
  itemClassName?: string
}

export function SegmentedControl<T extends string>({
  value,
  items,
  onValueChange,
  className,
  itemClassName,
}: SegmentedControlProps<T>) {
  return (
    <div
      className={cn(
        "flex w-full items-center gap-1 rounded-md border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-1 shadow-inner",
        className,
      )}
    >
      {items.map((item) => {
        const active = item.value === value

        return (
          <button
            key={item.value}
            type="button"
            data-testid={item.testId}
            disabled={item.disabled}
            onClick={() => onValueChange(item.value)}
            className={cn(
              "flex-1 inline-flex min-h-9 items-center justify-center gap-1.5 rounded-sm px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] transition-all duration-200",
              active
                ? "bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)] shadow-sm border border-[color:var(--px-shell-line)]"
                : "text-[color:var(--px-shell-muted)] hover:text-[color:var(--px-shell-ink)] disabled:cursor-not-allowed disabled:opacity-45 border border-transparent",
              itemClassName,
            )}
          >
            {item.icon ? <span className="flex h-4 w-4 items-center justify-center">{item.icon}</span> : null}
            <span>{item.label}</span>
          </button>
        )
      })}
    </div>
  )
}
