import type { MouseEventHandler } from "react"

interface SidebarProfileButtonProps {
  initial: string
  label: string
  subtitle: string
  onClick: MouseEventHandler<HTMLButtonElement>
  collapsed?: boolean
}

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
