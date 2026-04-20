import type { HTMLAttributes } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const pillVariants = cva(
  "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.18em]",
  {
    variants: {
      tone: {
        muted:
          "border-[color:var(--px-shell-line)] bg-white/70 text-[color:var(--px-shell-muted)]",
        accent:
          "border-[color:var(--px-shell-accent)]/20 bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]",
        ink: "border-transparent bg-[color:var(--px-shell-ink)] text-[color:var(--px-shell-surface)]",
      },
    },
    defaultVariants: {
      tone: "muted",
    },
  },
)

type PillProps = HTMLAttributes<HTMLDivElement> & VariantProps<typeof pillVariants>

export function Pill({ className, tone, ...props }: PillProps) {
  return <div className={cn(pillVariants({ tone }), className)} {...props} />
}
