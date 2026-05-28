/**
 * 侧边栏导航项组件
 * 基于 React Router NavLink，渲染带图标和文字的侧边栏导航链接
 */
import type { ReactNode } from "react"
import { NavLink } from "react-router-dom"

/** 侧边栏导航项，支持 collapsed 折叠模式（仅显示图标），active 高亮状态 */
export function SidebarNavItem({
  to,
  icon,
  label,
  collapsed = false,
  active,
}: {
  to: string
  icon: ReactNode
  label: string
  collapsed?: boolean
  active?: boolean
}) {
  return (
    <NavLink
      to={to}
      aria-label={label}
      title={label}
      className={({ isActive }) =>
        `flex items-center rounded-[16px] text-sm font-semibold transition-all duration-200 ${
          isActive || active
            ? "bg-[color:var(--px-shell-accent)] text-[color:var(--px-shell-accent-contrast)] shadow-[0_18px_38px_-26px_rgba(18,118,199,0.56)]"
            : "text-[color:var(--px-shell-muted)] hover:bg-[color:var(--px-shell-accent-soft)] hover:text-[color:var(--px-shell-ink)]"
        } ${
          collapsed ? "justify-center px-0 py-3.5" : "gap-3 px-4 py-3"
        }`
      }
    >
      <span className="shrink-0">{icon}</span>
      <span className={collapsed ? "sr-only" : "truncate"}>{label}</span>
    </NavLink>
  )
}
