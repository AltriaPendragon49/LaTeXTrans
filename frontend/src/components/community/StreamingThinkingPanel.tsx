import { Bot, CheckCircle2, ChevronDown, ChevronUp, Loader2, Search, Sparkles, XCircle } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"
import type { CommunityAgentToolTrace } from "@/types/community"

interface StreamingThinkingPanelProps {
  /** 是否正在执行（streaming） */
  isRunning: boolean
  /** 消息正文（streaming 增量） */
  streamingContent: string
  /** 工具调用追踪列表 */
  toolTrace: CommunityAgentToolTrace[]
  /** CSS 额外类名 */
  className?: string
}

function ToolTraceIcon({ trace }: { trace: CommunityAgentToolTrace }) {
  if (trace.status === "running") {
    return <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
  }
  if (trace.status === "completed") {
    return <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-emerald-400" />
  }
  if (trace.status === "failed") {
    return <XCircle className="h-3.5 w-3.5 shrink-0 text-rose-400" />
  }
  if (trace.kind === "search") {
    return <Search className="h-3.5 w-3.5 shrink-0 opacity-60" />
  }
  if (trace.kind === "reasoning") {
    return <Sparkles className="h-3.5 w-3.5 shrink-0 opacity-60" />
  }
  return <Bot className="h-3.5 w-3.5 shrink-0 opacity-60" />
}

function ToolTraceLine({ trace }: { trace: CommunityAgentToolTrace }) {
  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-xl px-3 py-2 text-xs transition-all duration-300",
        trace.status === "running"
          ? "bg-sky-500/10 text-sky-300"
          : trace.status === "completed"
            ? "bg-emerald-500/8 text-[var(--shell-text-soft)]"
            : trace.status === "failed"
              ? "bg-rose-500/8 text-rose-300"
              : "bg-[var(--shell-pill)] text-[var(--shell-text-muted)]",
      )}
    >
      <ToolTraceIcon trace={trace} />
      <div className="min-w-0 flex-1">
        <span className="font-medium">{trace.label}</span>
        {trace.detail ? (
          <span className="ml-1.5 truncate opacity-70">{trace.detail}</span>
        ) : null}
      </div>
    </div>
  )
}

/** 三个跳动小圆点的"Thinking..."指示器 */
function ThinkingDots() {
  return (
    <span className="inline-flex items-end gap-[3px]" aria-hidden>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="inline-block h-[5px] w-[5px] rounded-full bg-current opacity-70"
          style={{
            animation: `thinking-bounce 1.2s ease-in-out ${i * 0.18}s infinite`,
          }}
        />
      ))}
    </span>
  )
}

export function StreamingThinkingPanel({
  isRunning,
  streamingContent,
  toolTrace,
  className,
}: StreamingThinkingPanelProps) {
  const { t } = useTranslation()
  const [collapsed, setCollapsed] = useState(false)
  const contentRef = useRef<HTMLDivElement | null>(null)

  // 完成后自动折叠（延迟 2 秒），方便用户先看结果
  useEffect(() => {
    if (!isRunning && (streamingContent || toolTrace.length)) {
      const timer = window.setTimeout(() => setCollapsed(true), 2000)
      return () => window.clearTimeout(timer)
    }
    // 新一轮开始时展开
    if (isRunning) {
      setCollapsed(false)
    }
  }, [isRunning, streamingContent, toolTrace.length])

  // 没有任何内容时不渲染
  if (!isRunning && !toolTrace.length && !streamingContent) {
    return null
  }

  return (
    <>
      {/* 全局 keyframes 注入（SPA 只注入一次） */}
      <style>{`
        @keyframes thinking-bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40%            { transform: translateY(-4px); opacity: 1; }
        }
        @keyframes thinking-fade-in {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>

      <div
        data-testid="streaming-thinking-panel"
        className={cn(
          "overflow-hidden rounded-[22px] border transition-all duration-300",
          isRunning
            ? "border-sky-500/25 bg-[color:color-mix(in_srgb,var(--shell-surface)_92%,rgb(14_165_233)_8%)]"
            : "border-[color:var(--shell-border)] bg-[var(--shell-surface)]",
          className,
        )}
      >
        {/* 头部 */}
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          className="flex w-full items-center gap-2.5 px-4 py-3 text-left hover:bg-[var(--shell-pill)] transition-colors duration-150"
          aria-expanded={!collapsed}
        >
          <div className="relative flex h-5 w-5 items-center justify-center">
            {isRunning ? (
              <>
                {/* 外圈脉冲动画 */}
                <span className="absolute inset-0 animate-ping rounded-full bg-sky-400/25" />
                <Sparkles className="relative h-3.5 w-3.5 text-sky-400" />
              </>
            ) : (
              <Sparkles className="h-3.5 w-3.5 text-[var(--shell-icon)]" />
            )}
          </div>

          <span
            className={cn(
              "flex-1 text-xs font-semibold tracking-[0.08em] uppercase",
              isRunning ? "text-sky-300" : "text-[var(--shell-text-muted)]",
            )}
          >
            {isRunning ? (
              <span className="flex items-center gap-2">
                {t("community.conversation.thinking", "Thinking")}
                <ThinkingDots />
              </span>
            ) : (
              t("community.conversation.thinkingComplete", "Thinking finished")
            )}
          </span>

          {collapsed ? (
            <ChevronDown className="h-3.5 w-3.5 text-[var(--shell-text-muted)]" />
          ) : (
            <ChevronUp className="h-3.5 w-3.5 text-[var(--shell-text-muted)]" />
          )}
        </button>

        {/* 折叠内容 */}
        {!collapsed && (
          <div
            ref={contentRef}
            className="flex flex-col gap-1 px-3 pb-3"
            style={{ animation: "thinking-fade-in 0.25s ease both" }}
          >
            {/* 工具调用列表 */}
            {toolTrace.length > 0 && (
              <div className="flex flex-col gap-1">
                {toolTrace.map((trace) => (
                  <ToolTraceLine key={trace.id} trace={trace} />
                ))}
              </div>
            )}

            {/* 流式正文（streaming preview） */}
            {streamingContent && (
              <div className="mt-1.5 rounded-xl border border-[color:var(--shell-border)] bg-[var(--shell-bg)] px-3 py-2.5">
                <p className="text-xs leading-6 text-[var(--shell-text-soft)] whitespace-pre-wrap line-clamp-6">
                  {streamingContent}
                  {isRunning && (
                    <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-pulse bg-current align-middle opacity-80" />
                  )}
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
}
