/**
 * 侧边栏工具区域面板组件
 * 渲染侧边栏底部的工具区容器，带顶部分隔线
 */
import type { HTMLAttributes } from "react"

import { cn } from "@/lib/utils"

/** 侧边栏工具面板，用于放置语言选择器、主题切换等辅助控件 */
export function SidebarUtilityPanel({
  className,
  children,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "space-y-3 border-t border-[color:var(--px-shell-line)] pt-4",
        className,
      )}
      {...props}
    >
      {children}
    </div>
  )
}
