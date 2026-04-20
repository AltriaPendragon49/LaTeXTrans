import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

interface SectionHeadingProps {
  eyebrow?: ReactNode
  title: ReactNode
  description?: ReactNode
  aside?: ReactNode
  className?: string
}

export function SectionHeading({
  eyebrow,
  title,
  description,
  aside,
  className,
}: SectionHeadingProps) {
  return (
    <div className={cn("flex flex-col gap-3 px-1 lg:flex-row lg:items-end lg:justify-between", className)}>
      <div className="space-y-2">
        {eyebrow ? (
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[color:var(--px-shell-muted)]">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="text-2xl font-black text-[color:var(--px-shell-ink)]">{title}</h2>
        {description ? (
          <p className="max-w-3xl text-sm leading-6 text-[color:var(--px-shell-muted)]">{description}</p>
        ) : null}
      </div>
      {aside ? <div>{aside}</div> : null}
    </div>
  )
}
