/**
 * 编辑器外壳组件
 * 渲染表单式编辑器容器，包含工具栏、输入区和操作按钮区
 */
import type { FormHTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"

/** ComposerShell 组件 Props */
interface ComposerShellProps extends Omit<FormHTMLAttributes<HTMLFormElement>, "title"> {
  /**
   * 顶部工具栏区域
   */
  toolbar?: ReactNode
  /**
   * 输入区右侧操作槽位（如发送按钮）
   */
  actionSlot?: ReactNode
  /**
   * 底部脚注区域
   */
  footer?: ReactNode
  /**
   * 主体区域额外样式类名
   */
  bodyClassName?: string
}

/**
 * 编辑器外壳组件，顶层为 form 元素，包含可选的工具栏、内容区和底部脚注
 */
export function ComposerShell({
  toolbar,
  actionSlot,
  footer,
  bodyClassName,
  className,
  children,
  ...props
}: ComposerShellProps) {
  return (
    <form
      className={cn(
        "rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-[0_8px_30px_rgba(27,28,28,0.06)] transition-all focus-within:border-[color:var(--px-shell-accent)]/30 focus-within:ring-1 focus-within:ring-[color:var(--px-shell-accent)]/10",
        className,
      )}
      {...props}
    >
      {toolbar ? (
        <div className="border-b border-[color:var(--px-shell-line)]/70 px-4 py-3">
          {toolbar}
        </div>
      ) : null}

      <div className={cn("relative flex items-end gap-2 p-2", bodyClassName)}>
        <div className="min-w-0 flex-1">{children}</div>
        {actionSlot ? (
          <div className="flex shrink-0 items-center gap-1 pb-1 pr-1">
            {actionSlot}
          </div>
        ) : null}
      </div>

      {footer ? (
        <div className="border-t border-[color:var(--px-shell-line)]/70 px-4 py-2.5">
          {footer}
        </div>
      ) : null}
    </form>
  )
}
