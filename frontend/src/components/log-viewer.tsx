import { useRef, useEffect } from "react"
import type { HTMLAttributes } from "react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"

interface LogViewerProps extends HTMLAttributes<HTMLDivElement> {
    logs: string[]
    className?: string
}

export function LogViewer({ logs, className, ...props }: LogViewerProps) {
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
                "h-[300px] overflow-y-auto overflow-x-hidden rounded-md border bg-slate-950 p-4 font-mono text-xs text-slate-50 shadow-inner",
                className,
            )}
            ref={scrollRef}
            {...props}
        >
            {logs.length === 0 && <div className="text-slate-500 italic">{t("logs.waiting_for_logs")}</div>}
            {logs.map((log, index) => (
                <div key={index} className="whitespace-pre-wrap py-0.5 border-b border-slate-800/50 last:border-0 hover:bg-slate-900/50">
                    {log}
                </div>
            ))}
        </div>
    )
}
