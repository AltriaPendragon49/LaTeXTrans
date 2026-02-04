import { useRef, useEffect } from "react"

interface LogViewerProps {
    logs: string[]
}

export function LogViewer({ logs }: LogViewerProps) {
    const scrollRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
    }, [logs])

    return (
        <div className="rounded-md border bg-slate-950 text-slate-50 font-mono text-xs p-4 h-[300px] overflow-auto shadow-inner" ref={scrollRef}>
            {logs.length === 0 && <div className="text-slate-500 italic">Waiting for logs...</div>}
            {logs.map((log, index) => (
                <div key={index} className="whitespace-pre-wrap py-0.5 border-b border-slate-800/50 last:border-0 hover:bg-slate-900/50">
                    {log}
                </div>
            ))}
        </div>
    )
}
