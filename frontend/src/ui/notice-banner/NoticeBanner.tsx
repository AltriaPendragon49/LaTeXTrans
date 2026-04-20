import type { HTMLAttributes, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const noticeBannerVariants = cva(
  "flex items-start gap-3 rounded-xl border px-4 py-3",
  {
    variants: {
      tone: {
        neutral:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)]",
        info:
          "border-[color:var(--px-shell-info-line)] bg-[color:var(--px-shell-info-soft)] text-[color:var(--px-shell-info)]",
        warning:
          "border-[color:var(--px-shell-warning-line)] bg-[color:var(--px-shell-warning-soft)] text-[color:var(--px-shell-warning)]",
        success:
          "border-[color:var(--px-shell-success-line)] bg-[color:var(--px-shell-success-soft)] text-[color:var(--px-shell-success)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger)]",
      },
    },
    defaultVariants: {
      tone: "neutral",
    },
  },
)

interface NoticeBannerProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof noticeBannerVariants> {
  icon?: ReactNode
  title?: ReactNode
  description?: ReactNode
  action?: ReactNode
}

export function NoticeBanner({
  icon,
  title,
  description,
  action,
  tone,
  className,
  children,
  ...props
}: NoticeBannerProps) {
  return (
    <div className={cn(noticeBannerVariants({ tone }), className)} {...props}>
      {icon ? <div className="mt-0.5 shrink-0">{icon}</div> : null}

      <div className="min-w-0 flex-1 space-y-1">
        {title ? <p className="text-sm font-semibold text-current">{title}</p> : null}
        {description ? (
          <div className="text-sm leading-6 text-current/90">
            {description}
          </div>
        ) : null}
        {children}
      </div>

      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  )
}
