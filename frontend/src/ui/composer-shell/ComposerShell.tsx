import type { FormHTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"

interface ComposerShellProps extends Omit<FormHTMLAttributes<HTMLFormElement>, "title"> {
  toolbar?: ReactNode
  actionSlot?: ReactNode
  footer?: ReactNode
  bodyClassName?: string
}

export function ComposerShell({
  toolbar,
  actionSlot,
  footer,
  bodyClassName,
  className,
  children,
  ...props
}: ComposerShellProps) {
  return (
    <form
      className={cn(
        "rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-[0_8px_30px_rgba(27,28,28,0.06)] transition-all focus-within:border-[color:var(--px-shell-accent)]/30 focus-within:ring-1 focus-within:ring-[color:var(--px-shell-accent)]/10",
        className,
      )}
      {...props}
    >
      {toolbar ? (
        <div className="border-b border-[color:var(--px-shell-line)]/70 px-4 py-3">
          {toolbar}
        </div>
      ) : null}

      <div className={cn("relative flex items-end gap-2 p-2", bodyClassName)}>
        <div className="min-w-0 flex-1">{children}</div>
        {actionSlot ? (
          <div className="flex shrink-0 items-center gap-1 pb-1 pr-1">
            {actionSlot}
          </div>
        ) : null}
      </div>

      {footer ? (
        <div className="border-t border-[color:var(--px-shell-line)]/70 px-4 py-2.5">
          {footer}
        </div>
      ) : null}
    </form>
  )
}
