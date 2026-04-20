import type { ReactNode } from "react"
import { ChevronLeft } from "lucide-react"

import { Button } from "@/ui/button/Button"

export function SidebarShell({
  brand,
  nav,
  utility,
  collapsed,
  onToggleCollapse,
  collapseLabel,
}: {
  brand: ReactNode
  nav: ReactNode
  utility: ReactNode
  collapsed: boolean
  onToggleCollapse: () => void
  collapseLabel: string
}) {
  return (
    <aside
      data-collapsed={collapsed ? "true" : "false"}
      className={`sticky top-0 flex h-screen shrink-0 flex-col justify-between border-r border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] backdrop-blur-xl transition-[width,padding] duration-300 ${
        collapsed ? "w-[92px] px-3 py-5" : "w-[272px] px-5 py-6"
      }`}
    >
      <div className={collapsed ? "space-y-6" : "space-y-8"}>
        <div
          className={
            collapsed
              ? "flex justify-center"
              : "flex items-start justify-between gap-3"
          }
        >
          {brand}
          {!collapsed ? (
            <div className="shrink-0 pt-1">
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
