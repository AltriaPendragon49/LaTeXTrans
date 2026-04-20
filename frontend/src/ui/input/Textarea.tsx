import * as React from "react"

import { cn } from "@/lib/utils"

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<"textarea">
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "flex min-h-[140px] w-full resize-none rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-surface)] px-5 py-4 text-base text-[color:var(--px-shell-ink)] shadow-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/15 disabled:cursor-not-allowed disabled:opacity-50 placeholder:text-[color:var(--px-shell-muted)]",
      className,
    )}
    {...props}
  />
))

Textarea.displayName = "Textarea"

export { Textarea }
