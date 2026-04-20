import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] transition-colors focus:outline-none focus:ring-2 focus:ring-[color:var(--px-shell-accent)]/20 focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent)] text-white shadow-[var(--px-shell-shadow)] hover:bg-[color:var(--px-shell-accent-strong)]",
        secondary:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)] hover:border-[color:var(--px-shell-accent)]/30",
        destructive:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-strong)] text-[color:var(--px-shell-danger-contrast)] shadow-none hover:bg-[color:var(--px-shell-danger)]",
        outline:
          "border-[color:var(--px-shell-line)] bg-white/72 text-[color:var(--px-shell-muted)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  )
}

export { Badge, badgeVariants }
