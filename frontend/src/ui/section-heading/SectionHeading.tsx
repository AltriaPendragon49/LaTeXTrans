/**
 * 区域标题组件
 * 渲染区域标题、副标题和右侧附加内容的区块头部
 */
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

/** SectionHeading 组件 Props */
interface SectionHeadingProps {
  /** 标题上方小字 */
  eyebrow?: ReactNode
  /** 区域主标题 */
  title: ReactNode
  /** 可选描述文本 */
  description?: ReactNode
  /** 右侧附加内容 */
  aside?: ReactNode
  /** 额外样式 */
  className?: string
}

/** 区域标题，包含 eyebrow + h2 标题 + description，右侧可附加任意内容 */
export function SectionHeading({
  eyebrow,
  title,
  description,
  aside,
  className,
}: SectionHeadingProps) {
  return (
    <div className={cn("flex flex-col gap-3 px-1 lg:flex-row lg:items-end lg:justify-between", className)}>
      <div className="space-y-2">
        {eyebrow ? (
          <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[color:var(--px-shell-muted)]">
            {eyebrow}
          </p>
        ) : null}
        <h2 className="text-2xl font-black text-[color:var(--px-shell-ink)]">{title}</h2>
        {description ? (
          <p className="max-w-3xl text-sm leading-6 text-[color:var(--px-shell-muted)]">{description}</p>
        ) : null}
      </div>
      {aside ? <div>{aside}</div> : null}
    </div>
  )
}
