/**
 * 页面标题区组件
 * 渲染页面顶部的标题、描述、图标和操作按钮区域
 */
import type { HTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"

/** PageIntro 组件 Props */
interface PageIntroProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  /** 标题上方小字 */
  eyebrow?: ReactNode
  /** 页面主标题 */
  title: ReactNode
  /** 可选描述文本 */
  description?: ReactNode
  /** 可选图标 */
  icon?: ReactNode
  /** 可选元信息 */
  meta?: ReactNode
  /** 右侧操作按钮区域 */
  actions?: ReactNode
}

/** 页面标题区，左侧图标+标题+描述，右侧操作按钮，底部有分隔线 */
export function PageIntro({
  eyebrow,
  title,
  description,
  icon,
  meta,
  actions,
  className,
  ...props
}: PageIntroProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4 border-b border-[color:var(--px-shell-line)] pb-5 lg:flex-row lg:items-start lg:justify-between",
        className,
      )}
      {...props}
    >
      <div className="flex min-w-0 items-start gap-3">
        {icon ? (
          <div className="rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-3 text-[color:var(--px-shell-ink)]">
            {icon}
          </div>
        ) : null}

        <div className="min-w-0 space-y-1.5">
          {eyebrow ? (
            <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
              {eyebrow}
            </p>
          ) : null}
          <h1 className="text-2xl font-semibold tracking-tight text-[color:var(--px-shell-ink)]">
            {title}
          </h1>
          {description ? (
            <p className="max-w-3xl text-sm leading-6 text-[color:var(--px-shell-muted)]">
              {description}
            </p>
          ) : null}
          {meta ? (
            <div className="text-xs text-[color:var(--px-shell-muted)]">
              {meta}
            </div>
          ) : null}
        </div>
      </div>

      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {actions}
        </div>
      ) : null}
    </div>
  )
}
