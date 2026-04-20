import * as React from "react"

import { cn } from "@/lib/utils"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "flex min-h-11 w-full rounded-[22px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-surface)] px-4 py-2 text-base text-[color:var(--px-shell-ink)] shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/15 disabled:cursor-not-allowed disabled:opacity-50 file:mr-3 file:rounded-full file:border-0 file:bg-[color:var(--px-shell-accent-soft)] file:px-4 file:py-2 file:text-sm file:font-semibold file:text-[color:var(--px-shell-accent)] placeholder:text-[color:var(--px-shell-muted)] md:text-sm",
        className,
      )}
      {...props}
    />
  ),
)

Input.displayName = "Input"

export { Input }
