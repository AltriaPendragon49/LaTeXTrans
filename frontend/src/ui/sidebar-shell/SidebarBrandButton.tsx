import type { MouseEventHandler } from "react"
import { ChevronRight } from "lucide-react"

interface SidebarBrandButtonProps {
  brandName: string
  subtitle: string
  collapsed: boolean
  collapsedActionLabel?: string
  onClick: MouseEventHandler<HTMLButtonElement>
}

export function SidebarBrandButton({
  brandName,
  subtitle,
  collapsed,
  collapsedActionLabel,
  onClick,
}: SidebarBrandButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={collapsed ? collapsedActionLabel ?? brandName : brandName}
      title={collapsed ? collapsedActionLabel ?? brandName : brandName}
      className={`group inline-flex min-w-0 items-start text-left outline-none transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/25 ${
        collapsed
          ? "relative h-10 w-10 justify-center rounded-[16px] border border-transparent hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)]"
          : "flex-1"
      }`}
    >
      {collapsed ? (
        <>
          <span className="text-lg font-black uppercase tracking-[0.16em] text-[color:var(--px-shell-ink)] transition-all duration-200 group-hover:scale-90 group-hover:opacity-0 group-focus-visible:scale-90 group-focus-visible:opacity-0">
            PX
          </span>
          <span className="pointer-events-none absolute inset-0 flex items-center justify-center opacity-0 transition-all duration-200 group-hover:opacity-100 group-focus-visible:opacity-100">
            <ChevronRight className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
          </span>
        </>
      ) : (
        <span className="min-w-0">
          <span className="block text-[1.7rem] font-black tracking-[0.24em] text-[color:var(--px-shell-ink)] transition-colors duration-200 group-hover:text-[color:var(--px-shell-accent)]">
            {brandName}
          </span>
          <span className="mt-0.5 block text-[10px] font-semibold uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
            {subtitle}
          </span>
        </span>
      )}
    </button>
  )
}
