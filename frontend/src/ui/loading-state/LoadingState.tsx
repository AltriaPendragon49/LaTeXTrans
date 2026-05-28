/**
 * 加载状态组件
 * 渲染带旋转图标和文字的加载指示器，支持 inline 和 panel 两种布局
 */
import { Loader2 } from "lucide-react"
import { cva, type VariantProps } from "class-variance-authority"
import type { HTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"

/** 加载状态布局变体：inline（行内） / panel（卡片） */
const loadingStateVariants = cva("text-[color:var(--px-shell-muted)]", {
  variants: {
    layout: {
      inline: "flex items-center justify-center gap-3",
      panel:
        "rounded-[28px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] px-6 py-10 text-center shadow-[var(--px-shell-shadow)]",
    },
  },
  defaultVariants: {
    layout: "inline",
  },
})

/** LoadingState 组件 Props */
interface LoadingStateProps
  extends Omit<HTMLAttributes<HTMLDivElement>, "title">,
    VariantProps<typeof loadingStateVariants> {
  /** 加载提示文本 */
  label: ReactNode
  /** 可选副文本 */
  description?: ReactNode
}

/** 加载状态组件，inline 横向排列，panel 居中卡片式，均包含旋转动画图标 */
export function LoadingState({
  label,
  description,
  layout = "inline",
  className,
  ...props
}: LoadingStateProps) {
  if (layout === "panel") {
    return (
      <div className={cn(loadingStateVariants({ layout }), className)} {...props}>
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-accent)]">
          <Loader2 data-testid="loading-state-spinner" className="h-6 w-6 animate-spin" />
        </div>
        <div className="mx-auto mt-4 max-w-xl space-y-2">
          <p className="text-lg font-semibold text-[color:var(--px-shell-ink)]">{label}</p>
          {description ? (
            <p className="text-sm leading-6 text-[color:var(--px-shell-muted)]">{description}</p>
          ) : null}
        </div>
      </div>
    )
  }

  return (
    <div className={cn(loadingStateVariants({ layout }), className)} {...props}>
      <Loader2 data-testid="loading-state-spinner" className="h-5 w-5 animate-spin text-[color:var(--px-shell-accent)]" />
      <div className="space-y-1">
        <p className="text-sm font-medium text-[color:var(--px-shell-ink)]">{label}</p>
        {description ? (
          <p className="text-xs leading-5 text-[color:var(--px-shell-muted)]">{description}</p>
        ) : null}
      </div>
    </div>
  )
}
