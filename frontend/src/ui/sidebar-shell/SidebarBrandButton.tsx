import type { MouseEventHandler } from "react"
import { ChevronRight } from "lucide-react"

import collapsedLogo from "@/assets/logo-折叠.png"
import expandedLogo from "@/assets/logo-expanded-cropped.png"

interface SidebarBrandButtonProps {
  brandName: string
  subtitle: string
  collapsed: boolean
  showCollapsedActionHint?: boolean
  collapsedActionLabel?: string
  onClick: MouseEventHandler<HTMLButtonElement>
}

export function SidebarBrandButton({
  brandName,
  collapsed,
  showCollapsedActionHint = false,
  collapsedActionLabel,
  onClick,
}: SidebarBrandButtonProps) {
  const showExpandCue = collapsed && showCollapsedActionHint

  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={collapsed ? collapsedActionLabel ?? brandName : brandName}
      title={collapsed ? collapsedActionLabel ?? brandName : brandName}
      className={`group inline-flex min-w-0 items-start text-left outline-none transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/25 ${
        collapsed
          ? "relative h-11 w-11 justify-center rounded-[16px] border border-transparent transition-colors hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)]"
          : "flex-1 pr-11"
      }`}
    >
      <span className={collapsed ? "contents" : "hidden"}>
        <span
          className={`flex items-center justify-center transition-all duration-200 ${
            showExpandCue ? "scale-90 opacity-0" : ""
          } group-hover:scale-90 group-hover:opacity-0 group-focus-visible:scale-90 group-focus-visible:opacity-0`}
        >
          <img
            src={collapsedLogo}
            alt={collapsed ? brandName : ""}
            aria-hidden={collapsed ? undefined : true}
            className="h-10 w-10 object-contain"
          />
        </span>
        <span
          data-sidebar-expand-cue="true"
          className={`pointer-events-none absolute inset-0 flex items-center justify-center transition-all duration-200 ${
            showExpandCue ? "opacity-100" : "opacity-0"
          } group-hover:opacity-100 group-focus-visible:opacity-100`}
        >
          <ChevronRight className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
        </span>
      </span>
      <span className={collapsed ? "hidden" : "flex h-16 min-w-0 flex-1 items-center"}>
        <img
          src={expandedLogo}
          alt={collapsed ? "" : brandName}
          aria-hidden={collapsed ? true : undefined}
          className="h-auto w-full object-contain"
        />
      </span>
    </button>
  )
}
