import type { HTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"

interface RecordRowProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  icon?: ReactNode
  title: ReactNode
  meta?: ReactNode
  badge?: ReactNode
  action?: ReactNode
  detail?: ReactNode
  alert?: ReactNode
}

export function RecordRow({
  icon,
  title,
  meta,
  badge,
  action,
  detail,
  alert,
  className,
  children,
  ...props
}: RecordRowProps) {
  return (
    <div
      className={cn(
        "space-y-2 rounded-[20px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-3 shadow-sm",
        className,
      )}
      {...props}
    >
      <div className="flex items-start gap-2">
        {icon ? <div className="pt-0.5">{icon}</div> : null}

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <div className="min-w-0 flex-1 truncate text-sm font-medium text-[color:var(--px-shell-ink)]">
              {title}
            </div>
            {badge}
            {action}
          </div>
          {meta ? (
            <div className="mt-1 text-xs text-[color:var(--px-shell-muted)]">
              {meta}
            </div>
          ) : null}
        </div>
      </div>

      {detail ? <div>{detail}</div> : null}
      {children}
      {alert ? <div>{alert}</div> : null}
    </div>
  )
}
