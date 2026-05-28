/**
 * 记录行组件
 * 渲染一条数据记录，包含图标、标题、元信息、徽章、操作按钮和详情区域
 */
import type { HTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"

/** RecordRow 组件 Props */
interface RecordRowProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  /** 可选图标 */
  icon?: ReactNode
  /** 记录标题 */
  title: ReactNode
  /** 可选元信息（如时间、大小等） */
  meta?: ReactNode
  /** 可选徽章 */
  badge?: ReactNode
  /** 右侧操作区域 */
  action?: ReactNode
  /** 可展开的详情区域 */
  detail?: ReactNode
  /** 可选警告信息 */
  alert?: ReactNode
}

/** 记录行，包含图标+标题+元信息、徽章、操作按钮、详情区和警告区 */
export function RecordRow({
  icon,
  title,
  meta,
  badge,
  action,
  detail,
  alert,
  className,
  children,
  ...props
}: RecordRowProps) {
  return (
    <div
      className={cn(
        "space-y-2 rounded-[20px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-3 shadow-sm",
        className,
      )}
      {...props}
    >
      <div className="flex items-start gap-2">
        {icon ? <div className="pt-0.5">{icon}</div> : null}

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <div className="min-w-0 flex-1 truncate text-sm font-medium text-[color:var(--px-shell-ink)]">
              {title}
            </div>
            {badge}
            {action}
          </div>
          {meta ? (
            <div className="mt-1 text-xs text-[color:var(--px-shell-muted)]">
              {meta}
            </div>
          ) : null}
        </div>
      </div>

      {detail ? <div>{detail}</div> : null}
      {children}
      {alert ? <div>{alert}</div> : null}
    </div>
  )
}
