import type { HTMLAttributes, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const infoTileVariants = cva(
  "rounded-[22px] border",
  {
    variants: {
      tone: {
        panel:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)]",
        muted:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)]",
        accent:
          "border-[color:var(--px-shell-accent)]/15 bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-ink)]",
        warning:
          "border-[color:var(--px-shell-warning-line)] bg-[color:var(--px-shell-warning-soft)] text-[color:var(--px-shell-ink)]",
        success:
          "border-[color:var(--px-shell-success-line)] bg-[color:var(--px-shell-success-soft)] text-[color:var(--px-shell-ink)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-ink)]",
      },
      size: {
        default: "px-4 py-3",
        compact: "px-3 py-2.5",
      },
    },
    defaultVariants: {
      tone: "panel",
      size: "default",
    },
  },
)

interface InfoTileProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof infoTileVariants> {
  icon?: ReactNode
  title: ReactNode
  description?: ReactNode
  value?: ReactNode
  trailing?: ReactNode
  titleClassName?: string
  valueClassName?: string
}

export function InfoTile({
  icon,
  title,
  description,
  value,
  trailing,
  tone,
  size,
  className,
  titleClassName,
  valueClassName,
  children,
  ...props
}: InfoTileProps) {
  return (
    <div
      className={cn(infoTileVariants({ tone, size }), className)}
      {...props}
    >
      <div className="flex items-start gap-3">
        {icon ? (
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:color-mix(in_srgb,var(--px-shell-panel)_78%,white)] text-[color:var(--px-shell-accent)] shadow-sm">
            {icon}
          </div>
        ) : null}

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1 space-y-1">
              <div
                className={cn(
                  "text-xs font-bold uppercase tracking-[0.16em] text-[color:var(--px-shell-muted)]",
                  titleClassName,
                )}
              >
                {title}
              </div>
              {description ? (
                <div className="text-sm leading-6 text-[color:var(--px-shell-ink)]">
                  {description}
                </div>
              ) : null}
            </div>

            {value || trailing ? (
              <div className="flex shrink-0 items-center gap-3">
                {value ? (
                  <div
                    className={cn(
                      "text-right text-sm font-semibold text-[color:var(--px-shell-ink)]",
                      valueClassName,
                    )}
                  >
                    {value}
                  </div>
                ) : null}
                {trailing}
              </div>
            ) : null}
          </div>

          {children ? <div className="mt-3">{children}</div> : null}
        </div>
      </div>
    </div>
  )
}
