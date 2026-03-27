import {
  ArrowUpRight,
  Bot,
  Loader2,
  Download,
  Eye,
  Languages,
  Link2,
  ScrollText,
  Sparkles,
  Timer,
} from "lucide-react"
import { useEffect, useRef, useState, type FormEvent, type RefObject } from "react"
import { useTranslation } from "react-i18next"

import { PaperPreviewReader } from "@/components/community/PaperPreviewReader"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Switch } from "@/components/ui/switch"
import { cn } from "@/lib/utils"
import type {
  CommunityAgentCitation,
  CommunityAgentMode,
  CommunityPaper,
  CommunityPaperPreviewResponse,
  CommunityPaperReader,
  CommunityPaperReaderMode,
  CommunityConversationTurn,
} from "@/types/community"

const SPLIT_STORAGE_KEY = "community-paper-reader-split-ratio"
const DEFAULT_SPLIT_RATIO = 0.88
const MIN_READER_WIDTH = 720
const MIN_AGENT_WIDTH = 260
const READER_SELECTION_HIGHLIGHT_NAME = "paper-detail-reader-selection"

function getTraceStatusClass(status: string) {
  switch (status) {
    case "completed":
      return "border-emerald-500/30 bg-emerald-500/10 text-emerald-100"
    case "fallback":
      return "border-amber-500/30 bg-amber-500/10 text-amber-100"
    default:
      return "border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-text-soft)]"
  }
}

function formatConversationTimestamp(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return ""
  }

  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
}

function clampSplitRatio(ratio: number, width: number) {
  if (!Number.isFinite(ratio) || !Number.isFinite(width) || width <= 0) {
    return DEFAULT_SPLIT_RATIO
  }
  const minRatio = MIN_READER_WIDTH / width
  const maxRatio = 1 - MIN_AGENT_WIDTH / width
  return Math.min(Math.max(ratio, minRatio), maxRatio)
}

interface PaperDetailWorkspaceProps {
  paper: CommunityPaper
  preview: CommunityPaperPreviewResponse | null
  readerState: "ready" | "warming" | "unavailable"
  reader: CommunityPaperReader | null
  preferredMode: CommunityPaperReaderMode
  availableModes: CommunityPaperReaderMode[]
  stageLabel: string
  softBanner: string | null
  canLeaveHint: string | null
  originalSourceUrl: string | null
  abstractText: string
  readerHighlight: boolean
  previewRef: RefObject<HTMLDivElement | null>
  canTranslate: boolean
  canViewProgress: boolean
  canDownload: boolean
  actionError: string | null
  onTranslate: () => void
  onViewProgress: () => void
  onPreview: () => void
  onDownload: () => void
  onModeChange: (mode: CommunityPaperReaderMode) => void
  agentTurns: CommunityConversationTurn[]
  agentInput: string
  agentMode: CommunityAgentMode
  externalSearchEnabled: boolean
  readerSelection: {
    text: string
    anchor_id: string | null
    mode: CommunityPaperReaderMode
  } | null
  agentBusy: boolean
  agentError: string | null
  onAgentInputChange: (value: string) => void
  onAgentModeChange: (mode: CommunityAgentMode) => void
  onExternalSearchChange: (value: boolean) => void
  onAgentSubmit: () => void
  onSelectionClear: () => void
  onQuickExplain: () => void
  onQuickSummary: () => void
  onCitationOpen: (citation: CommunityAgentCitation) => void
}

export function PaperDetailWorkspace({
  paper,
  preview,
  readerState,
  reader,
  preferredMode,
  availableModes,
  stageLabel,
  softBanner,
  canLeaveHint,
  originalSourceUrl,
  abstractText,
  readerHighlight,
  previewRef,
  canTranslate,
  canViewProgress,
  canDownload,
  actionError,
  onTranslate,
  onViewProgress,
  onPreview,
  onDownload,
  onModeChange,
  agentTurns,
  agentInput,
  agentMode,
  externalSearchEnabled,
  readerSelection,
  agentBusy,
  agentError,
  onAgentInputChange,
  onAgentModeChange,
  onExternalSearchChange,
  onAgentSubmit,
  onSelectionClear,
  onQuickExplain,
  onQuickSummary,
  onCitationOpen,
}: PaperDetailWorkspaceProps) {
  const { t } = useTranslation()
  const containerRef = useRef<HTMLDivElement | null>(null)
  const [splitRatio, setSplitRatio] = useState(() => {
    if (typeof window === "undefined") {
      return DEFAULT_SPLIT_RATIO
    }
    const stored = Number(window.localStorage.getItem(SPLIT_STORAGE_KEY) ?? DEFAULT_SPLIT_RATIO)
    return Number.isFinite(stored) ? stored : DEFAULT_SPLIT_RATIO
  })
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window === "undefined" ? true : window.innerWidth >= 1280,
  )
  const messageListRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(SPLIT_STORAGE_KEY, String(splitRatio))
    }
  }, [splitRatio])

  useEffect(() => {
    if (typeof window === "undefined") {
      return undefined
    }

    const handleResize = () => {
      setIsDesktop(window.innerWidth >= 1280)
    }

    handleResize()
    window.addEventListener("resize", handleResize)
    return () => window.removeEventListener("resize", handleResize)
  }, [])

  useEffect(() => {
    const container = messageListRef.current
    if (!container) {
      return
    }

    const frameId = window.requestAnimationFrame(() => {
      if (typeof container.scrollTo === "function") {
        container.scrollTo({
          top: container.scrollHeight,
          behavior: "smooth",
        })
        return
      }
      container.scrollTop = container.scrollHeight
    })

    return () => window.cancelAnimationFrame(frameId)
  }, [agentBusy, agentTurns])

  const sourceAvailable = availableModes.includes("source")
  const translatedAvailable = availableModes.includes("translated")
  const sourceKind = preferredMode === "source" ? reader?.source?.kind ?? null : null
  const sourceHtmlContent =
    preferredMode === "source" && reader?.source?.kind === "source_html"
      ? (reader.source.html_content ?? null)
      : null
  const translatedResource = preferredMode === "translated" ? reader?.translated ?? null : null
  const translatedHtmlContent =
    preferredMode === "translated"
      ? (reader?.translated?.html_content ?? preview?.html_content ?? null)
      : null
  const translatedPreviewAvailable =
    preferredMode === "translated" &&
    (Boolean(preview?.html_content) ||
      reader?.translated?.kind === "preview_html" ||
      paper.latest_asset?.asset_type === "preview_html")
  const translatedPreviewPayload: CommunityPaperPreviewResponse | null =
    preview ??
    (preferredMode === "translated" &&
      reader?.translated?.kind === "preview_html" &&
      reader.translated.html_content
      ? {
        paper_id: paper.id,
        task_id: paper.community_selected_task_id ?? null,
        asset:
          paper.latest_asset?.asset_type === "preview_html"
            ? paper.latest_asset
            : {
              id: paper.community_selected_asset_id ?? "preview-html",
              task_id: paper.community_selected_task_id,
              asset_type: "preview_html",
              file_name: "preview.html",
              mime_type: "text/html",
              created_at: null,
            },
        html_content: reader.translated.html_content,
        generated_at: paper.latest_asset?.created_at ?? null,
      }
      : null)
  const translatedPdfFallback =
    preferredMode === "translated" && translatedResource?.kind === "translated_pdf"
      ? translatedResource
      : null
  const sourceDocumentUrl =
    preferredMode === "source"
      ? sourceKind === "source_pdf"
        ? reader?.source?.url ?? (paper.arxiv_id ? `https://arxiv.org/pdf/${paper.arxiv_id}.pdf` : null)
        : sourceKind === "external_arxiv_html"
          ? paper.arxiv_id
            ? `https://arxiv.org/pdf/${paper.arxiv_id}.pdf`
            : null
          : reader?.source?.url ?? null
      : null
  const sourceExternalLink =
    preferredMode === "source"
      ? reader?.source?.url ??
      (paper.arxiv_id ? `https://arxiv.org/abs/${paper.arxiv_id}` : originalSourceUrl)
      : null

  function handleResizeStart(event: React.PointerEvent<HTMLDivElement>) {
    const container = containerRef.current
    if (!container) {
      return
    }

    event.preventDefault()
    const rect = container.getBoundingClientRect()

    const handlePointerMove = (pointerEvent: PointerEvent) => {
      const nextWidth = pointerEvent.clientX - rect.left
      const nextRatio = clampSplitRatio(nextWidth / rect.width, rect.width)
      setSplitRatio(nextRatio)
    }

    const handlePointerUp = () => {
      window.removeEventListener("pointermove", handlePointerMove)
      window.removeEventListener("pointerup", handlePointerUp)
    }

    window.addEventListener("pointermove", handlePointerMove)
    window.addEventListener("pointerup", handlePointerUp)
  }

  const desktopGridColumns = `${splitRatio}fr 12px ${Math.max(1 - splitRatio, 0.18)}fr`

  function handleAgentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (agentBusy || !agentInput.trim()) {
      return
    }
    onAgentSubmit()
  }

  return (
    <>
      <style>{`::highlight(${READER_SELECTION_HIGHLIGHT_NAME}) { background-color: rgba(250, 204, 21, 0.45); }`}</style>
      <div
        ref={containerRef}
        data-testid="paper-detail-top-panels"
        className={cn("flex-1 w-full h-full relative", isDesktop ? "grid" : "flex flex-col overflow-y-auto")}
        style={isDesktop ? { gridTemplateColumns: desktopGridColumns } : undefined}
      >
        <section
          data-testid="paper-detail-reader-panel"
          className={cn(
            "flex h-full min-w-0 flex-col overflow-hidden bg-surface-container-lowest transition-all [&_[data-reader-anchor-active='true']]:rounded-md [&_[data-reader-anchor-active='true']]:ring-2 [&_[data-reader-anchor-active='true']]:ring-primary/70 [&_[data-reader-anchor-active='true']]:ring-offset-2 [&_[data-reader-anchor-active='true']]:ring-offset-surface-container-lowest [&_[data-reader-selection-active='true']]:rounded-sm [&_[data-reader-selection-active='true']]:bg-primary-fixed/40 [&_[data-reader-selection-active='true']]:shadow-[inset_0_0_0_1px_var(--color-primary-fixed-dim)]",
            readerHighlight ? "ring-2 ring-primary/60" : "",
            isDesktop ? "border-r border-outline-variant/30" : "border-b border-outline-variant/30 min-h-[50vh]"
          )}
        >
          <div className="h-10 shrink-0 hidden lg:flex items-center justify-between px-4 border-b border-outline-variant/30 bg-surface-container-low hidden lg:flex">
            <div className="flex items-center gap-2 text-sm text-on-surface-variant font-medium">
              <ScrollText className="w-4 h-4 text-primary" />
              {preferredMode === "source" ? "LaTeX Document Reader" : "Translated Document Reader"}
            </div>
            {sourceExternalLink ? (
              <a
                href={sourceExternalLink}
                target="_blank"
                rel="noreferrer noopener"
                className="inline-flex items-center gap-2 text-xs text-on-surface-variant transition hover:text-on-surface"
              >
                <Link2 className="h-3.5 w-3.5" />
                {t("community.detail.originalSource")}
              </a>
            ) : null}
          </div>

          <div className="flex-1 overflow-auto bg-surface-container-lowest">
            {preferredMode === "source" ? (
              sourceHtmlContent ? (
                <article
                  data-testid="paper-source-reader"
                  className="h-full bg-surface-container-lowest px-6 py-6 text-on-surface sm:px-8 lg:px-10 lg:py-8 [&_article]:mx-auto [&_article]:max-w-[1040px] [&_article]:space-y-6 [&_figcaption]:text-sm [&_figcaption]:leading-6 [&_figcaption]:text-on-surface-variant [&_figure]:my-8 [&_figure]:overflow-x-auto [&_h1]:mt-8 [&_h1]:text-4xl [&_h1]:font-semibold [&_h1]:tracking-[-0.04em] [&_h2]:mt-10 [&_h2]:text-[1.85rem] [&_h2]:font-semibold [&_h2]:tracking-[-0.03em] [&_h3]:mt-8 [&_h3]:text-[1.35rem] [&_h3]:font-semibold [&_li]:leading-8 [&_ol]:space-y-3 [&_p]:text-[17px] [&_p]:leading-8 [&_pre]:overflow-x-auto [&_pre]:rounded-2xl [&_pre]:bg-surface-container [&_pre]:p-4 [&_pre]:text-sm [&_pre]:text-on-surface [&_table]:w-full [&_table]:overflow-x-auto [&_table]:text-sm [&_td]:border [&_td]:border-outline-variant/30 [&_td]:px-3 [&_td]:py-2 [&_th]:border [&_th]:border-outline-variant/30 [&_th]:bg-surface-container-low [&_th]:px-3 [&_th]:py-2 [&_ul]:space-y-3 [&_math]:overflow-x-auto [&_math]:block [&_math]:py-2"
                  dangerouslySetInnerHTML={{ __html: sourceHtmlContent }}
                />
              ) : sourceDocumentUrl ? (
                <iframe
                  data-testid="paper-source-pdf-reader"
                  title={`${paper.title} PDF`}
                  src={sourceDocumentUrl}
                  className="h-full w-full border-0 bg-surface-container-lowest"
                />
              ) : (
                <article
                  data-testid="paper-source-reader"
                  className="flex h-full flex-col gap-4 px-10 py-8"
                >
                  <h2 className="text-2xl font-semibold text-on-surface">{paper.title}</h2>
                  <p className="max-w-4xl text-base leading-8 text-on-surface-variant">{abstractText}</p>
                  {originalSourceUrl ? (
                    <a
                      href={originalSourceUrl}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="inline-flex items-center gap-2 text-sm text-primary underline-offset-4 hover:underline"
                    >
                      <Link2 className="h-4 w-4" />
                      {t("community.detail.originalSource")}
                    </a>
                  ) : null}
                </article>
              )
            ) : preferredMode === "translated" && readerState === "warming" ? (
              <div className="h-full p-3 bg-surface-container-lowest">
                <PaperPreviewReader ref={previewRef} paperId={paper.id} initialPreview={null} readerState={readerState} />
              </div>
            ) : translatedPreviewAvailable ? (
              <div className="h-full p-3 bg-surface-container-lowest">
                <PaperPreviewReader
                  ref={previewRef}
                  paperId={paper.id}
                  initialPreview={translatedPreviewPayload}
                  readerState={readerState}
                />
              </div>
            ) : translatedHtmlContent ? (
              (
                <article
                  data-testid="paper-translated-reader"
                  className="h-full bg-surface-container-lowest px-6 py-6 text-on-surface sm:px-8 lg:px-10 lg:py-8 [&_article]:mx-auto [&_article]:max-w-[1040px] [&_article]:space-y-6 [&_figcaption]:text-sm [&_figcaption]:leading-6 [&_figcaption]:text-on-surface-variant [&_figure]:my-8 [&_figure]:overflow-x-auto [&_h1]:mt-8 [&_h1]:text-4xl [&_h1]:font-semibold [&_h1]:tracking-[-0.04em] [&_h2]:mt-10 [&_h2]:text-[1.85rem] [&_h2]:font-semibold [&_h2]:tracking-[-0.03em] [&_h3]:mt-8 [&_h3]:text-[1.35rem] [&_h3]:font-semibold [&_li]:leading-8 [&_ol]:space-y-3 [&_p]:text-[17px] [&_p]:leading-8 [&_pre]:overflow-x-auto [&_pre]:rounded-2xl [&_pre]:bg-surface-container [&_pre]:p-4 [&_pre]:text-sm [&_pre]:text-on-surface [&_table]:w-full [&_table]:overflow-x-auto [&_table]:text-sm [&_td]:border [&_td]:border-outline-variant/30 [&_td]:px-3 [&_td]:py-2 [&_th]:border [&_th]:border-outline-variant/30 [&_th]:bg-surface-container-low [&_th]:px-3 [&_th]:py-2 [&_ul]:space-y-3 [&_math]:overflow-x-auto [&_math]:block [&_math]:py-2"
                  dangerouslySetInnerHTML={{ __html: translatedHtmlContent }}
                />
              )
            ) : translatedPdfFallback?.kind === "translated_pdf" ? (
              <article
                data-testid="paper-translated-pdf-fallback"
                className="flex h-full flex-col items-center justify-center gap-4 px-10 py-8 text-center"
              >
                <h2 className="text-2xl font-semibold text-on-surface">
                  {t("community.card.assetType.translated_pdf")}
                </h2>
                <p className="max-w-2xl text-base leading-7 text-on-surface-variant">{stageLabel}</p>
                <Button type="button" onClick={onDownload} variant="default" className="rounded-full">
                  <Download className="h-4 w-4 mr-2" />
                  {t("community.actions.download")}
                </Button>
              </article>
            ) : (
              <article
                data-testid="paper-translated-reader"
                className="flex h-full flex-col gap-4 px-10 py-8"
              >
                <h2 className="text-2xl font-semibold text-on-surface">{paper.title}</h2>
                <p className="max-w-4xl text-base leading-8 text-on-surface-variant">{abstractText}</p>
              </article>
            )}
          </div>
        </section>

        {isDesktop ? (
          <div
            data-testid="paper-detail-resize-handle"
            role="separator"
            aria-orientation="vertical"
            onPointerDown={handleResizeStart}
            className="group flex cursor-col-resize items-stretch justify-center w-3 h-full z-10 -ml-1.5"
          >
            <div className="flex h-full w-full items-center justify-center group-hover:bg-primary/10 transition-colors">
              <div className="h-16 w-1 rounded-full bg-outline-variant/50 group-hover:bg-primary transition-colors" />
            </div>
          </div>
        ) : null}

        <aside
          data-testid="paper-detail-agent-panel"
          className={cn(
            "flex flex-col bg-surface-container-low relative shrink-0",
            isDesktop ? "h-full" : "min-h-[500px]"
          )}
        >
          <div className="p-4 border-b border-outline-variant/30 flex items-center justify-between bg-surface-container-lowest shrink-0">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <span className="font-medium text-on-surface">Curator AI Agent</span>
            </div>
            <span className="px-2 py-0.5 rounded text-[10px] font-medium tracking-wider uppercase bg-surface-container text-on-surface-variant">
              Alpha
            </span>
          </div>

          <div ref={messageListRef} className="flex-1 overflow-y-auto p-4 space-y-4">
            {agentTurns.length === 0 ? (
               <div className="h-full flex flex-col items-center justify-center text-center p-6 text-on-surface-variant/70 space-y-4">
                  <div className="w-16 h-16 rounded-2xl bg-surface-container flex items-center justify-center mb-2">
                     <Sparkles className="w-8 h-8 text-primary/40" />
                  </div>
                  <p className="text-sm">I can help you analyze this document, summarize sections, or explain complex concepts.</p>
               </div>
            ) : null}

            {agentTurns.map((turn) => {
              const assistantRun = turn.role === "assistant" ? turn.run : null
              const citations = assistantRun?.citations ?? []
              const toolTrace = assistantRun?.tool_trace ?? []
              return (
                <div key={turn.id} className={cn("flex flex-col gap-1", turn.role === "user" ? "items-end" : "items-start")}>
                  <div className="flex items-center gap-2 px-1 mb-1">
                    <span className="text-[11px] font-medium text-on-surface-variant">
                      {turn.role === "user" ? t("community.conversation.userLabel") : t("community.conversation.agentLabel")}
                    </span>
                    <span className="text-[10px] text-on-surface-variant/60">{formatConversationTimestamp(turn.created_at)}</span>
                  </div>
                  <div
                    className={cn(
                      "px-4 py-3 text-sm leading-relaxed max-w-[90%]",
                      turn.role === "user"
                        ? "bg-primary text-on-primary rounded-2xl rounded-tr-sm"
                        : "bg-surface-container-lowest border border-outline-variant/30 text-on-surface rounded-2xl rounded-tl-sm"
                    )}
                  >
                    <p className="whitespace-pre-wrap leading-6">{turn.content}</p>

                    {citations.length ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {citations.map((citation) => (
                          <button
                            key={citation.id}
                            type="button"
                            onClick={() => void onCitationOpen(citation)}
                            className="inline-flex items-center gap-1.5 rounded-full border border-outline-variant/30 bg-surface-container px-3 py-1.5 text-xs text-on-surface transition hover:bg-surface-container-high shrink-0"
                          >
                            <span className="truncate max-w-[180px]">{citation.title}</span>
                            <ArrowUpRight className="h-3 w-3 text-on-surface-variant" />
                          </button>
                        ))}
                      </div>
                    ) : null}

                    {toolTrace.length ? (
                      <div className="mt-3 grid gap-2">
                        {toolTrace.map((entry) => (
                          <div
                            key={entry.id}
                            className={cn(
                              "flex items-start gap-2.5 rounded-xl border border-outline-variant/20 px-3 py-2 text-xs",
                              entry.status === "completed" ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300" :
                              entry.status === "fallback" ? "bg-amber-500/10 text-amber-700 dark:text-amber-300" :
                              "bg-surface-container-low text-on-surface-variant"
                            )}
                          >
                            {entry.kind === "reasoning" ? (
                              <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0 opacity-70" />
                            ) : (
                              <Bot className="mt-0.5 h-3.5 w-3.5 shrink-0 opacity-70" />
                            )}
                            <div className="min-w-0">
                              <div className="font-medium">{entry.label}</div>
                              {entry.detail ? (
                                <div className="mt-0.5 text-[11px] opacity-80">{entry.detail}</div>
                              ) : null}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>
                </div>
              )
            })}

            {agentBusy ? (
              <div className="flex gap-2">
                <div className="px-4 py-3 bg-surface-container-lowest border border-outline-variant/30 text-on-surface rounded-2xl rounded-tl-sm text-sm flex items-center gap-2">
                  <div className="flex gap-1 items-center h-5">
                    <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                  <span className="text-on-surface-variant text-xs ml-1">{t("community.conversation.running")}</span>
                </div>
              </div>
            ) : null}

            {agentError ? (
              <div className="rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
                {agentError}
              </div>
            ) : null}
          </div>

          <div className="p-4 bg-surface-container-lowest border-t border-outline-variant/30 shrink-0">
            {readerSelection ? (
              <div className="mb-3 rounded-xl bg-surface-container p-3 border border-outline-variant/30">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-1.5 text-xs font-medium text-primary">
                    <ScrollText className="w-3.5 h-3.5" />
                    {t("community.detail.selectionContextTitle")}
                  </div>
                  <button
                    type="button"
                    onClick={onSelectionClear}
                    className="text-xs text-on-surface-variant hover:text-on-surface transition-colors"
                  >
                    {t("common.actions.cancel")}
                  </button>
                </div>
                <div className="text-[13px] leading-relaxed text-on-surface-variant line-clamp-3 pl-2 border-l-2 border-primary/30">
                  {readerSelection.text}
                </div>
              </div>
            ) : null}

            <form onSubmit={handleAgentSubmit} className="relative">
              <textarea
                value={agentInput}
                onChange={(event) => onAgentInputChange(event.target.value)}
                placeholder={t("community.agent.placeholder")}
                rows={1}
                className="w-full bg-surface-container rounded-2xl outline-none placeholder:text-on-surface-variant/50 text-sm text-on-surface px-4 py-3 pr-12 resize-none min-h-[44px] max-h-[120px] focus:ring-1 focus:ring-primary focus:bg-surface-container-lowest border border-transparent focus:border-outline-variant/30 transition-all"
                style={{ fieldSizing: "content" } as any}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    if (!agentBusy && agentInput.trim()) {
                      onAgentSubmit();
                    }
                  }
                }}
              />
              <button 
                type="submit"
                disabled={agentBusy || !agentInput.trim()}
                className="absolute right-2 top-2 p-1.5 rounded-xl bg-primary text-on-primary hover:opacity-90 transition-opacity disabled:opacity-50 disabled:bg-surface-container-highest disabled:text-on-surface-variant"
              >
                {agentBusy ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowUpRight className="w-4 h-4" />}
              </button>
            </form>
            
            <div className="flex items-center justify-between mt-3 text-[11px] text-on-surface-variant">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => onAgentModeChange(agentMode === "chat" ? "deep_research" : "chat")}
                  className={cn(
                    "flex items-center gap-1 hover:text-on-surface transition-colors",
                    agentMode === "deep_research" ? "text-primary font-medium" : ""
                  )}
                >
                  <Sparkles className="w-3 h-3" />
                  Deep Research
                </button>
                <div className="w-px h-3 bg-outline-variant/50" />
                <button
                  type="button"
                  onClick={() => onExternalSearchChange(!externalSearchEnabled)}
                  className={cn(
                    "flex items-center gap-1 hover:text-on-surface transition-colors",
                    externalSearchEnabled ? "text-primary font-medium" : ""
                  )}
                >
                  <Link2 className="w-3 h-3" />
                  Web Search
                </button>
              </div>
              <span className="hidden sm:inline opacity-70">Shift + Return to break line</span>
            </div>
          </div>
        </aside>
      </div>
    </>
  )
}
