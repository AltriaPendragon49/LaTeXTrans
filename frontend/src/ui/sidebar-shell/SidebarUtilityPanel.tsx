import type { HTMLAttributes } from "react"

import { cn } from "@/lib/utils"

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
