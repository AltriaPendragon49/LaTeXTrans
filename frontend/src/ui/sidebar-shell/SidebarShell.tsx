import type { ReactNode } from "react"
import { ChevronLeft } from "lucide-react"

import { Button } from "@/ui/button/Button"

export function SidebarShell({
  brand,
  nav,
  utility,
  collapsed,
  onToggleCollapse,
  onHoverChange,
  collapseLabel,
}: {
  brand: ReactNode
  nav: ReactNode
  utility: ReactNode
  collapsed: boolean
  onToggleCollapse: () => void
  onHoverChange?: (hovered: boolean) => void
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
