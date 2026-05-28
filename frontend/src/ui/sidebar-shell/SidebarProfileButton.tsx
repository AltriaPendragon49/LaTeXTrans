/**
 * 侧边栏用户信息按钮组件
 * 渲染用户的头像首字母、名称和副标题的可点击按钮
 */
import type { MouseEventHandler } from "react"

/** SidebarProfileButton 组件 Props */
interface SidebarProfileButtonProps {
  /** 用户首字母 */
  initial: string
  /** 用户名称 */
  label: string
  /** 副标题（如邮箱） */
  subtitle: string
  /** 点击回调 */
  onClick: MouseEventHandler<HTMLButtonElement>
  /** 是否折叠模式 */
  collapsed?: boolean
}

/** 侧边栏用户信息按钮，折叠时仅显示头像首字母，展开时显示完整信息 */
export function SidebarProfileButton({
  initial,
  label,
  subtitle,
  onClick,
  collapsed = false,
}: SidebarProfileButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className={`flex w-full rounded-[18px] text-left transition-all duration-200 hover:bg-[color:var(--px-shell-panel-strong)] ${
        collapsed ? "justify-center px-0 py-2" : "items-center gap-3 px-2 py-2"
      }`}
    >
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[color:var(--px-shell-accent-soft)] text-sm font-bold uppercase text-[color:var(--px-shell-accent)]">
        {initial}
      </div>
      <div className={collapsed ? "sr-only" : "min-w-0"}>
        <div className="truncate text-sm font-semibold text-[color:var(--px-shell-ink)]">
          {label}
        </div>
        <div className="text-xs text-[color:var(--px-shell-muted)]">
          {subtitle}
        </div>
      </div>
    </button>
  )
}
