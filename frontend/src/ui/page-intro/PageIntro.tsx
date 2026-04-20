import type { HTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"

interface PageIntroProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  eyebrow?: ReactNode
  title: ReactNode
  description?: ReactNode
  icon?: ReactNode
  meta?: ReactNode
  actions?: ReactNode
}

export function PageIntro({
  eyebrow,
  title,
  description,
  icon,
  meta,
  actions,
  className,
  ...props
}: PageIntroProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4 border-b border-[color:var(--px-shell-line)] pb-5 lg:flex-row lg:items-start lg:justify-between",
        className,
      )}
      {...props}
    >
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <div className="rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-3 text-[color:var(--px-shell-ink)]">
            {icon}
          </div>
        ) : null}

        <div className="min-w-0 space-y-1.5">
          {eyebrow ? (
            <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
              {eyebrow}
            </p>
          ) : null}
          <h1 className="text-2xl font-semibold tracking-tight text-[color:var(--px-shell-ink)]">
            {title}
          </h1>
          {description ? (
            <p className="max-w-3xl text-sm leading-6 text-[color:var(--px-shell-muted)]">
              {description}
            </p>
          ) : null}
          {meta ? (
            <div className="text-xs text-[color:var(--px-shell-muted)]">
              {meta}
            </div>
          ) : null}
        </div>
      </div>

      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {actions}
        </div>
      ) : null}
    </div>
  )
}
