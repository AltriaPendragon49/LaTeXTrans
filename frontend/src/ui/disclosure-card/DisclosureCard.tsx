import type { HTMLAttributes, ReactNode } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"

import { cn } from "@/lib/utils"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/ui/primitives/collapsible"

interface DisclosureCardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: ReactNode
  eyebrow?: ReactNode
  description?: ReactNode
  headerAside?: ReactNode
  contentClassName?: string
}

export function DisclosureCard({
  open,
  onOpenChange,
  title,
  eyebrow,
  description,
  headerAside,
  contentClassName,
  className,
  children,
  ...props
}: DisclosureCardProps) {
  return (
    <Collapsible open={open} onOpenChange={onOpenChange}>
      <div
        className={cn(
          "overflow-hidden rounded-[22px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-none",
          className,
        )}
        {...props}
      >
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex w-full items-start justify-between gap-3 px-4 py-4 text-left transition-colors hover:bg-[color:var(--px-shell-panel-strong)]"
          >
            <div className="min-w-0 flex-1 space-y-1.5">
              {eyebrow ? (
                <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[color:var(--px-shell-muted)]">
                  {eyebrow}
                </div>
              ) : null}
              <div className="text-sm font-semibold text-[color:var(--px-shell-ink)]">{title}</div>
              {description ? (
                <div className="text-xs leading-6 text-[color:var(--px-shell-muted)]">{description}</div>
              ) : null}
            </div>

            <div className="flex shrink-0 items-center gap-3 pl-2">
              {headerAside ? <div className="shrink-0">{headerAside}</div> : null}
              {open ? (
                <ChevronUp className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
              ) : (
                <ChevronDown className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
              )}
            </div>
          </button>
        </CollapsibleTrigger>

        <CollapsibleContent className="border-t border-[color:var(--px-shell-line)]">
          <div className={cn("px-4 py-4 text-sm text-[color:var(--px-shell-muted)]", contentClassName)}>
            {children}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}
