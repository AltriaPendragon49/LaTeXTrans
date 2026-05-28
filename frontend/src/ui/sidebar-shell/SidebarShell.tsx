/**
 * 侧边栏外壳组件
 * 渲染完整的侧边栏布局，包含品牌区、导航区和工具区，支持折叠/展开切换
 */
import type { ReactNode } from "react"
import { ChevronLeft } from "lucide-react"

import { Button } from "@/ui/button/Button"

/** SidebarShell 组件 Props */
export function SidebarShell({
  brand,
  nav,
  utility,
  collapsed,
  onToggleCollapse,
  onHoverChange,
  collapseLabel,
}: {
  /** 品牌 Logo 区域（如 SidebarBrandButton） */
  brand: ReactNode
  /** 导航区域 */
  nav: ReactNode
  /** 工具区域（如语言选择器、主题切换） */
  utility: ReactNode
  /** 是否折叠 */
  collapsed: boolean
  /** 切换折叠回调 */
  onToggleCollapse: () => void
  /** hover 状态变化回调（用于触发展开提示） */
  onHoverChange?: (hovered: boolean) => void
  /** 折叠按钮的无障碍标签 */
  collapseLabel: string
}) {
  return (
    <aside
      data-collapsed={collapsed ? "true" : "false"}
      onMouseEnter={() => onHoverChange?.(true)}
      onMouseLeave={() => onHoverChange?.(false)}
      className={`sticky top-0 flex h-screen shrink-0 flex-col justify-between border-r border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] backdrop-blur-xl ${
        collapsed ? "w-[92px] px-3 py-5" : "w-[244px] px-4 py-5"
      }`}
    >
      <div className={collapsed ? "space-y-6" : "space-y-6"}>
        <div
          className={
            collapsed
              ? "flex justify-center"
              : "relative flex items-start"
          }
        >
          {brand}
          {!collapsed ? (
            <div className="absolute right-0 top-1/2 shrink-0 -translate-y-1/2">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={onToggleCollapse}
                aria-label={collapseLabel}
                title={collapseLabel}
                className="h-10 w-10 shrink-0 rounded-[16px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-muted)] hover:bg-white hover:text-[color:var(--px-shell-ink)]"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
            </div>
          ) : null}
        </div>
        {nav}
      </div>
      <div>{utility}</div>
    </aside>
  )
}
