import type { HTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/ui/card/Card"

interface SectionCardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  icon?: ReactNode
  title: ReactNode
  description?: ReactNode
  headerAside?: ReactNode
  headerClassName?: string
  contentClassName?: string
  iconClassName?: string
}

export function SectionCard({
  icon,
  title,
  description,
  headerAside,
  headerClassName,
  contentClassName,
  iconClassName,
  className,
  children,
  ...props
}: SectionCardProps) {
  return (
    <Card className={cn("overflow-hidden shadow-none", className)} {...props}>
      <CardHeader
        className={cn(
          "flex flex-row items-start justify-between gap-4 bg-white/48",
          headerClassName,
        )}
      >
        <div className="flex min-w-0 items-start gap-3">
          {icon ? (
            <div
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-accent)]",
                iconClassName,
              )}
            >
              {icon}
            </div>
          ) : null}

          <div className="min-w-0 space-y-1">
            <CardTitle className="text-base font-bold tracking-tight">{title}</CardTitle>
            {description ? (
              <CardDescription className="text-xs leading-5">{description}</CardDescription>
            ) : null}
          </div>
        </div>

        {headerAside ? <div className="shrink-0">{headerAside}</div> : null}
      </CardHeader>

      <CardContent className={cn("px-6 py-5", contentClassName)}>
        {children}
      </CardContent>
    </Card>
  )
}
