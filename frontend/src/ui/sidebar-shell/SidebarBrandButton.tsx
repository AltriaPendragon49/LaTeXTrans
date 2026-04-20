import type { MouseEventHandler } from "react"

interface SidebarBrandButtonProps {
  brandName: string
  subtitle: string
  collapsed: boolean
  onClick: MouseEventHandler<HTMLButtonElement>
}

export function SidebarBrandButton({
  brandName,
  subtitle,
  collapsed,
  onClick,
}: SidebarBrandButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={brandName}
      title={brandName}
      className={`group inline-flex min-w-0 items-start text-left outline-none transition-colors duration-200 focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/25 ${
        collapsed ? "justify-center" : "w-full"
      }`}
    >
      {collapsed ? (
        <span className="text-lg font-black uppercase tracking-[0.16em] text-[color:var(--px-shell-ink)]">
          PX
        </span>
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
