import type { HTMLAttributes, ReactNode } from "react"

import { Button } from "@/ui/button/Button"
import { cn } from "@/lib/utils"

interface FilterToolbarOption {
  value: string
  label: ReactNode
  icon?: ReactNode
}

interface FilterToolbarProps extends HTMLAttributes<HTMLDivElement> {
  options: FilterToolbarOption[]
  value: string
  onValueChange: (value: string) => void
  meta?: ReactNode
  actions?: ReactNode
}

export function FilterToolbar({
  options,
  value,
  onValueChange,
  meta,
  actions,
  className,
  ...props
}: FilterToolbarProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 border-b border-[color:var(--px-shell-line)] pb-3 lg:flex-row lg:items-center lg:justify-between",
        className,
      )}
      {...props}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="inline-flex flex-wrap gap-2 rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-1 shadow-[0_12px_28px_rgba(15,23,42,0.05)]">
          {options.map((option) => {
            const active = option.value === value

            return (
              <Button
                key={option.value}
                type="button"
                variant={active ? "secondary" : "ghost"}
                onClick={() => onValueChange(option.value)}
                className={cn(
                  "min-h-10 rounded-full px-4 py-2 text-sm",
                  active
                    ? "bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)] shadow-[inset_0_0_0_1px_rgba(18,118,199,0.16)]"
                    : "text-[color:var(--px-shell-muted)] hover:bg-[color:var(--px-shell-panel)] hover:text-[color:var(--px-shell-ink)]",
                )}
                aria-pressed={active}
              >
                {option.icon ? <span className="flex items-center">{option.icon}</span> : null}
                <span>{option.label}</span>
              </Button>
            )
          })}
        </div>

        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>

      {meta ? <div className="flex flex-wrap items-center gap-3">{meta}</div> : null}
    </div>
  )
}
