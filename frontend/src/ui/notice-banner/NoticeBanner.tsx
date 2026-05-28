/**
 * 通知横幅组件
 * 渲染带图标、标题、描述和操作的横幅通知，支持多种语义色调
 */
import type { HTMLAttributes, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/** 通知横幅色调变体：neutral / info / warning / success / danger */
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

/** NoticeBanner 组件 Props */
interface NoticeBannerProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof noticeBannerVariants> {
  /** 可选图标 */
  icon?: ReactNode
  /** 可选标题 */
  title?: ReactNode
  /** 可选描述 */
  description?: ReactNode
  /** 可选操作按钮 */
  action?: ReactNode
}

/** 通知横幅，左侧图标+正文，右侧操作按钮 */
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
