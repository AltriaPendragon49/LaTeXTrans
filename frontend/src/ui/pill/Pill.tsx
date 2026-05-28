/**
 * 药丸标签组件
 * 渲染小巧的圆角药丸形标签，支持 muted / accent / ink 三种色调
 */
import type { HTMLAttributes } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/** 药丸标签样式变体：muted / accent / ink */
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

/** 药丸标签，极简的文本标签组件 */
export function Pill({ className, tone, ...props }: PillProps) {
  return <div className={cn(pillVariants({ tone }), className)} {...props} />
}
