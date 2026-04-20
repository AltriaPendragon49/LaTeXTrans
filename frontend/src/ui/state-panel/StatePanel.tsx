import type { HTMLAttributes, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const statePanelVariants = cva(
  "rounded-[32px] border px-6 py-14 text-center shadow-[var(--px-shell-shadow)]",
  {
    variants: {
      tone: {
        neutral:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger)] shadow-none",
      },
      borderStyle: {
        solid: "",
        dashed: "border-dashed",
      },
    },
    defaultVariants: {
      tone: "neutral",
      borderStyle: "solid",
    },
  },
)

const statePanelIconVariants = cva(
  "mx-auto flex h-16 w-16 items-center justify-center rounded-full border",
  {
    variants: {
      tone: {
        neutral:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger)]",
      },
    },
    defaultVariants: {
      tone: "neutral",
    },
  },
)

interface StatePanelProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof statePanelVariants> {
  icon?: ReactNode
  meta?: ReactNode
  title: ReactNode
  description?: ReactNode
  detail?: ReactNode
  actions?: ReactNode
}

export function StatePanel({
  icon,
  meta,
  title,
  description,
  detail,
  actions,
  tone = "neutral",
  borderStyle = "solid",
  className,
  ...props
}: StatePanelProps) {
  return (
    <div
      className={cn(statePanelVariants({ tone, borderStyle }), className)}
      {...props}
    >
      {icon ? (
        <div className={cn(statePanelIconVariants({ tone }))}>
          {icon}
        </div>
      ) : null}

      <div className={cn("mx-auto max-w-xl space-y-2", icon ? "mt-5" : "")}>
        {meta ? (
          <div className="text-[10px] font-black uppercase tracking-[0.22em] text-current/60">
            {meta}
          </div>
        ) : null}
        <h2 className="text-2xl font-semibold text-current">{title}</h2>
        {description ? (
          <p className="text-sm leading-7 text-current/80">{description}</p>
        ) : null}
        {detail ? (
          <div className="pt-1 text-sm text-current/75">{detail}</div>
        ) : null}
      </div>

      {actions ? (
        <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
          {actions}
        </div>
      ) : null}
    </div>
  )
}
