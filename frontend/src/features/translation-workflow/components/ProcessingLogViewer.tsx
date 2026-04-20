import type { HTMLAttributes } from "react"
import { useEffect, useRef } from "react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"

interface ProcessingLogViewerProps extends HTMLAttributes<HTMLDivElement> {
  logs: string[]
  className?: string
}

export function ProcessingLogViewer({ logs, className, ...props }: ProcessingLogViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const { t } = useTranslation()

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs])

  return (
    <div
      className={cn(
        "h-[300px] overflow-y-auto overflow-x-hidden rounded-md border border-[color:color-mix(in_srgb,var(--px-shell-line)_88%,rgba(23,20,17,0.14))] bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_85%,var(--px-shell-surface))] p-4 font-mono text-xs text-[color:var(--px-shell-ink)] shadow-inner",
        className,
      )}
      ref={scrollRef}
      {...props}
    >
      {logs.length === 0 ? (
        <div className="italic text-[color:var(--px-shell-muted)]">{t("logs.waiting_for_logs")}</div>
      ) : null}
      {logs.map((log, index) => (
        <div
          key={index}
          className="whitespace-pre-wrap border-b border-[color:color-mix(in_srgb,var(--px-shell-line)_88%,rgba(23,20,17,0.14))]/80 py-0.5 last:border-0 hover:bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_76%,black_24%)]"
        >
          {log}
        </div>
      ))}
    </div>
  )
}
