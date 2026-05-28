/**
 * 状态徽章组件
 * 渲染带可选图标的药丸形状态标签，支持多种语义色调（muted/accent/info/success/warning/danger）
 */
import type { HTMLAttributes, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/** 状态徽章样式变体 */
const statusBadgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em]",
  {
    variants: {
      tone: {
        muted:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-muted)]",
        accent:
          "border-[color:var(--px-shell-accent)]/20 bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]",
        info:
          "border-[color:var(--px-shell-info-line)] bg-[color:var(--px-shell-info-soft)] text-[color:var(--px-shell-info)]",
        success:
          "border-[color:var(--px-shell-success-line)] bg-[color:var(--px-shell-success-soft)] text-[color:var(--px-shell-success)]",
        warning:
          "border-[color:var(--px-shell-warning-line)] bg-[color:var(--px-shell-warning-soft)] text-[color:var(--px-shell-warning)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger)]",
      },
      size: {
        sm: "px-2.5 py-1 text-[10px]",
        md: "px-3 py-1.5 text-[11px]",
      },
    },
    defaultVariants: {
      tone: "muted",
      size: "sm",
    },
  },
)

type StatusBadgeProps = HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof statusBadgeVariants> & {
    /** 可选图标 */
    icon?: ReactNode
  }

/** 状态徽章，常用于表示任务状态、标签等 */
export function StatusBadge({
  className,
  tone,
  size,
  icon,
  children,
  ...props
}: StatusBadgeProps) {
  return (
    <div className={cn(statusBadgeVariants({ tone, size }), className)} {...props}>
      {icon ? <span className="flex h-3.5 w-3.5 items-center justify-center">{icon}</span> : null}
      <span>{children}</span>
    </div>
  )
}
