import {
  ArrowUpRight,
  Bot,
  Loader2,
  Download,
  Link2,
  ScrollText,
  Sparkles,
} from "lucide-react"
import { useEffect, useRef, useState, type FormEvent, type RefObject } from "react"
import { useTranslation } from "react-i18next"

import { API_BASE_URL } from "@/api-base"
import { PaperPreviewReader } from "@/components/community/PaperPreviewReader"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type {
  CommunityAgentCitation,
  CommunityAgentMode,
  CommunityPaper,
  CommunityPaperPreviewResponse,
  CommunityPaperReader,
  CommunityPaperReaderMode,
  CommunityConversationTurn,
  ReaderSelectionContext,
  PaperAnnotation,
  PaperAnnotationOverlayRect,
} from "@/types/community"

const SPLIT_STORAGE_KEY = "community-paper-reader-split-ratio-v2"
const DEFAULT_SPLIT_RATIO = 0.65
const MIN_READER_WIDTH = 720
const MIN_AGENT_WIDTH = 260
const READER_SELECTION_HIGHLIGHT_NAME = "paper-detail-reader-selection"

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

function getHighlightOverlayColor(color: string) {
  switch (color) {
    case "red":
      return "rgba(255, 82, 82, 0.3)"
    case "orange":
      return "rgba(255, 171, 64, 0.3)"
    case "green":
      return "rgba(105, 240, 174, 0.3)"
    case "blue":
      return "rgba(68, 138, 255, 0.3)"
    case "purple":
      return "rgba(179, 136, 255, 0.3)"
    case "fuchsia":
      return "rgba(255, 64, 129, 0.3)"
    case "cyan":
      return "rgba(24, 255, 255, 0.3)"
    default:
      return "rgba(255, 215, 64, 0.3)"
  }
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
  translatedPdfPreviewLoading: boolean
  translatedPdfPreviewUrl: string | null
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
  readerSelection: ReaderSelectionContext | null
  onReaderSelectionChange: (selection: ReaderSelectionContext | null) => void
  onSaveAnnotation: (annotation: PaperAnnotation) => void
  onRemoveHighlightForSelection: (selection: ReaderSelectionContext) => void
  annotations: PaperAnnotation[]
  annotationOverlayRects: PaperAnnotationOverlayRect[]
  onFocusAnnotation: (annotation: PaperAnnotation) => void
  agentContext: ReaderSelectionContext | null
  agentBusy: boolean
  agentError: string | null
  onAgentInputChange: (value: string) => void
  onAgentModeChange: (mode: CommunityAgentMode) => void
  onExternalSearchChange: (value: boolean) => void
  onAgentSubmit: () => void
  onSelectionClear: () => void
  onAskAI?: (selection: ReaderSelectionContext) => void
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
  stageLabel,
  originalSourceUrl,
  abstractText,
  readerHighlight,
  previewRef,
  translatedPdfPreviewLoading,
  translatedPdfPreviewUrl,
  onDownload,
  agentTurns,
  agentInput,
  agentMode,
  externalSearchEnabled,
  readerSelection,
  onReaderSelectionChange,
  onSaveAnnotation,
  onRemoveHighlightForSelection,
  annotations,
  annotationOverlayRects,
  onFocusAnnotation,
  agentContext,
  agentBusy,
  agentError,
  onAgentInputChange,
  onAgentModeChange,
  onExternalSearchChange,
  onAgentSubmit,
  onSelectionClear,
  onAskAI,
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
    typeof window === "undefined" ? true : window.innerWidth >= 1024,
  )
  const [activeTab, setActiveTab] = useState<"Assistant" | "My Notes" | "Comments" | "Similar">("Assistant")
  const [expandedAnnotationId, setExpandedAnnotationId] = useState<string | null>(null)
  const messageListRef = useRef<HTMLDivElement | null>(null)
  // removed context menu state
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
      setIsDesktop(window.innerWidth >= 1024)
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

  const sourceHtmlContent =
    (preferredMode === "source") && reader?.source?.kind === "source_html"
      ? (reader.source.html_content ?? null)
      : null
  const translatedResource = (preferredMode === "translated" || preferredMode === "translated_html" || preferredMode === "translated_pdf") ? reader?.translated ?? null : null
  const translatedHtmlContent =
    (preferredMode === "translated" || preferredMode === "translated_html")
      ? (reader?.translated?.html_content ?? preview?.html_content ?? null)
      : null
  const translatedPreviewAvailable =
    (preferredMode === "translated" || preferredMode === "translated_html") &&
    (Boolean(preview?.html_content) ||
      reader?.translated?.kind === "preview_html" ||
      paper.latest_asset?.asset_type === "preview_html")
  const translatedPreviewPayload: CommunityPaperPreviewResponse | null =
    preview ??
    ((preferredMode === "translated" || preferredMode === "translated_html") &&
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
    (preferredMode === "translated" || preferredMode === "translated_pdf") && translatedResource?.kind === "translated_pdf"
      ? translatedResource
      : null
  const hasTranslatedPdf =
    paper.trans_status === "completed" &&
    Boolean(paper.assets?.translated_pdf || translatedPdfFallback || paper.community_selected_task_id)
  const translatedPdfFallbackUrl = translatedPdfPreviewUrl ?? (
    hasTranslatedPdf ? `${API_BASE_URL}/api/papers/${paper.id}/translated-pdf` : null
  )
  const noteAnnotations = [...annotations].reverse()
  const sourceDocumentUrl =
    (preferredMode === "source")
      ? `${API_BASE_URL}/api/papers/${paper.id}/source-pdf`
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

  function applySelectionHighlight(color: string) {
    if (!readerSelection?.range) {
      return
    }

    let savedRange: Range
    try {
      savedRange = readerSelection.range.cloneRange()
    } catch {
      return
    }

    onSaveAnnotation({
      id: crypto.randomUUID(),
      text: readerSelection.text,
      range: savedRange,
      anchor_id: readerSelection.anchor_id,
      mode: readerSelection.mode,
      color,
      note: readerSelection.note || "",
    })
    onReaderSelectionChange(null)
    window.getSelection()?.removeAllRanges()
  }

  return (
    <>
      <style>{`
        ::highlight(${READER_SELECTION_HIGHLIGHT_NAME}) { background-color: rgba(250, 204, 21, 0.45); }
        ::highlight(paper-annotation-red) { background-color: rgba(255, 82, 82, 0.33); }
        ::highlight(paper-annotation-orange) { background-color: rgba(255, 171, 64, 0.33); }
        ::highlight(paper-annotation-yellow) { background-color: rgba(255, 215, 64, 0.33); }
        ::highlight(paper-annotation-green) { background-color: rgba(105, 240, 174, 0.33); }
        ::highlight(paper-annotation-blue) { background-color: rgba(68, 138, 255, 0.33); }
        ::highlight(paper-annotation-purple) { background-color: rgba(179, 136, 255, 0.33); }
        ::highlight(paper-annotation-fuchsia) { background-color: rgba(255, 64, 129, 0.33); }
        ::highlight(paper-annotation-cyan) { background-color: rgba(24, 255, 255, 0.33); }
      `}</style>
      <div
        ref={containerRef}
        data-testid="paper-detail-top-panels"
        className={cn("flex-1 min-h-0 min-w-0 w-full h-full relative", isDesktop ? "grid" : "flex flex-col overflow-y-auto")}
        style={isDesktop ? { gridTemplateColumns: desktopGridColumns } : undefined}
      >
        <section
          data-testid="paper-detail-reader-panel"
          className={cn(
            "flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-surface-container-lowest transition-all [&_[data-reader-anchor-active='true']]:rounded-md [&_[data-reader-anchor-active='true']]:ring-2 [&_[data-reader-anchor-active='true']]:ring-primary/70 [&_[data-reader-anchor-active='true']]:ring-offset-2 [&_[data-reader-anchor-active='true']]:ring-offset-surface-container-lowest [&_[data-reader-selection-active='true']]:rounded-sm [&_[data-reader-selection-active='true']]:bg-primary-fixed/40 [&_[data-reader-selection-active='true']]:shadow-[inset_0_0_0_1px_var(--color-primary-fixed-dim)]",
            readerHighlight ? "ring-2 ring-primary/60" : "",
            isDesktop ? "" : "border-b border-outline-variant/30 min-h-[50vh]"
          )}
        >

          <div 
            data-testid="paper-reader-scroll-root"
            className="relative flex-1 overflow-auto bg-surface-container-lowest [&_article::selection]:bg-yellow-200 [&_article::selection]:text-gray-900"
          >
            {annotationOverlayRects.length > 0 ? (
              <div aria-hidden className="pointer-events-none absolute inset-0 z-[3]">
                {annotationOverlayRects.map((rect) => (
                  <span
                    key={rect.id}
                    className="absolute rounded-[2px]"
                    style={{
                      top: rect.top,
                      left: rect.left,
                      width: rect.width,
                      height: rect.height,
                      backgroundColor: getHighlightOverlayColor(rect.color),
                    }}
                  />
                ))}
              </div>
            ) : null}

            {preferredMode === "source" ? (
              sourceDocumentUrl ? (
                <iframe
                  data-testid="paper-source-pdf-reader"
                  title={`${paper.title} PDF`}
                  src={sourceDocumentUrl}
                  className="h-full w-full border-0 bg-surface-container-lowest"
                />
              ) : sourceHtmlContent ? (
                <article
                  data-testid="paper-source-reader"
                  className="h-full bg-surface-container-lowest px-6 py-6 text-on-surface sm:px-8 lg:px-10 lg:py-8 [&_article]:mx-auto [&_article]:max-w-[1040px] [&_article]:space-y-6 [&_figcaption]:text-sm [&_figcaption]:leading-6 [&_figcaption]:text-on-surface-variant [&_figure]:my-8 [&_figure]:overflow-x-auto [&_h1]:mt-8 [&_h1]:text-4xl [&_h1]:font-semibold [&_h1]:tracking-[-0.04em] [&_h2]:mt-10 [&_h2]:text-[1.85rem] [&_h2]:font-semibold [&_h2]:tracking-[-0.03em] [&_h3]:mt-8 [&_h3]:text-[1.35rem] [&_h3]:font-semibold [&_li]:leading-8 [&_ol]:space-y-3 [&_p]:text-[17px] [&_p]:leading-8 [&_pre]:overflow-x-auto [&_pre]:rounded-2xl [&_pre]:bg-surface-container [&_pre]:p-4 [&_pre]:text-sm [&_pre]:text-on-surface [&_table]:w-full [&_table]:overflow-x-auto [&_table]:text-sm [&_td]:border [&_td]:border-outline-variant/30 [&_td]:px-3 [&_td]:py-2 [&_th]:border [&_th]:border-outline-variant/30 [&_th]:bg-surface-container-low [&_th]:px-3 [&_th]:py-2 [&_ul]:space-y-3 [&_math]:overflow-x-auto [&_math]:block [&_math]:py-2"
                  dangerouslySetInnerHTML={{ __html: sourceHtmlContent }}
                />
              ) : (
                <article
                  data-testid="paper-source-reader"
                  className="flex h-full flex-col gap-4 px-10 py-8"
                >
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
            ) : (preferredMode === "translated_html" || preferredMode === "translated") && readerState === "warming" ? (
              <div className="h-full bg-surface-container-lowest">
                <PaperPreviewReader ref={previewRef} paperId={paper.id} initialPreview={null} readerState={readerState} />
              </div>
            ) : translatedPreviewAvailable ? (
              <div className="h-full bg-surface-container-lowest">
                <PaperPreviewReader
                  ref={previewRef}
                  paperId={paper.id}
                  initialPreview={translatedPreviewPayload}
                  readerState={readerState}
                />
              </div>
            ) : translatedHtmlContent && (preferredMode === "translated_html" || preferredMode === "translated") ? (
              (
                <article
                  data-testid="paper-translated-reader"
                  className="h-full bg-surface-container-lowest px-6 py-6 text-on-surface sm:px-8 lg:px-10 lg:py-8 [&_article]:mx-auto [&_article]:max-w-[1040px] [&_article]:space-y-6 [&_figcaption]:text-sm [&_figcaption]:leading-6 [&_figcaption]:text-on-surface-variant [&_figure]:my-8 [&_figure]:overflow-x-auto [&_h1]:mt-8 [&_h1]:text-4xl [&_h1]:font-semibold [&_h1]:tracking-[-0.04em] [&_h2]:mt-10 [&_h2]:text-[1.85rem] [&_h2]:font-semibold [&_h2]:tracking-[-0.03em] [&_h3]:mt-8 [&_h3]:text-[1.35rem] [&_h3]:font-semibold [&_li]:leading-8 [&_ol]:space-y-3 [&_p]:text-[17px] [&_p]:leading-8 [&_pre]:overflow-x-auto [&_pre]:rounded-2xl [&_pre]:bg-surface-container [&_pre]:p-4 [&_pre]:text-sm [&_pre]:text-on-surface [&_table]:w-full [&_table]:overflow-x-auto [&_table]:text-sm [&_td]:border [&_td]:border-outline-variant/30 [&_td]:px-3 [&_td]:py-2 [&_th]:border [&_th]:border-outline-variant/30 [&_th]:bg-surface-container-low [&_th]:px-3 [&_th]:py-2 [&_ul]:space-y-3 [&_math]:overflow-x-auto [&_math]:block [&_math]:py-2"
                  dangerouslySetInnerHTML={{ __html: translatedHtmlContent }}
                />
              )
            ) : preferredMode === "translated_pdf" && translatedPdfPreviewLoading ? (
              <article
                data-testid="paper-translated-pdf-loading"
                className="flex h-full flex-col items-center justify-center gap-4 px-10 py-8 text-center"
              >
                <p className="max-w-2xl text-base leading-7 text-on-surface-variant">
                  {t("community.reader.loading")}
                </p>
              </article>
            ) : (preferredMode === "translated_pdf" || preferredMode === "translated") && translatedPdfFallbackUrl ? (
              <iframe
                data-testid="paper-translated-pdf-reader"
                title={`${paper.title} Translated PDF`}
                src={translatedPdfFallbackUrl}
                className="h-full w-full border-0 bg-surface-container-lowest"
              />
            ) : (preferredMode === "translated_pdf" || preferredMode === "translated") && translatedPdfFallback?.kind === "translated_pdf" ? (
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
                <p className="max-w-4xl text-base leading-8 text-on-surface-variant">{abstractText}</p>
              </article>
            )}
          </div>

          {readerSelection?.position && (
            <div
              data-reader-selection-toolbar="true"
              className="fixed z-50 rounded-2xl border border-slate-200 bg-white p-4 text-slate-900 shadow-2xl min-w-[320px] animate-in fade-in zoom-in-95 duration-150"
              style={{ 
                top: Math.max(80, readerSelection.position.y), 
                left: readerSelection.position.x, 
                transform: 'translateX(-50%)' 
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <textarea
                value={readerSelection.note || ""}
                onChange={(e) => onReaderSelectionChange({ ...readerSelection, note: e.target.value })}
                placeholder="Add text here..."
                className="mb-4 min-h-[40px] w-full resize-none border-none bg-white text-sm text-slate-900 outline-none placeholder:text-slate-500"
              />
              
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-1.5">
                  {[
                    { id: 'red', color: '#ff5252' },
                    { id: 'orange', color: '#ffab40' },
                    { id: 'yellow', color: '#ffd740' },
                    { id: 'green', color: '#69f0ae' },
                    { id: 'blue', color: '#448aff' },
                    { id: 'purple', color: '#b388ff' },
                    { id: 'fuchsia', color: '#ff4081' },
                    { id: 'cyan', color: '#18ffff' },
                  ].map((item) => (
                    <button
                      type="button"
                      key={item.id}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => applySelectionHighlight(item.id)}
                      className={cn(
                        "w-5 h-5 rounded-full transition-transform hover:scale-125 border-2",
                        readerSelection.color === item.id ? "border-primary" : "border-transparent"
                      )}
                      style={{ backgroundColor: item.color }}
                    />
                  ))}
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => {
                      if (readerSelection) {
                        onRemoveHighlightForSelection(readerSelection)
                      }
                    }}
                    className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:bg-blue-50 hover:text-blue-600"
                  >
                    <ScrollText className="w-3.5 h-3.5" />
                    取消高亮
                  </button>

                  <button
                    type="button"
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => {
                      if (onAskAI && readerSelection) {
                        onAskAI(readerSelection)
                      }
                    }}
                    className="flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-medium text-blue-600 transition-colors hover:bg-blue-50"
                  >
                    <Sparkles className="w-3.5 h-3.5" />
                    Ask AI
                  </button>
                </div>
              </div>
            </div>
          )}
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
            "flex min-h-0 min-w-0 flex-col overflow-hidden bg-surface-container-low relative shrink-0",
            isDesktop ? "h-full" : "min-h-[500px]"
          )}
        >
          <div className="flex bg-surface-container-lowest border-b border-outline-variant/30 shrink-0 px-2 pt-2 gap-1 overflow-hidden no-scrollbar">
            {(["Assistant", "My Notes", "Comments", "Similar"] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={cn(
                  "px-4 py-2.5 text-sm font-medium border-b-2 transition-colors relative -bottom-[1px] whitespace-nowrap outline-none",
                  activeTab === tab
                    ? "border-primary text-primary"
                    : "border-transparent text-on-surface-variant hover:text-on-surface hover:border-outline-variant/50"
                )}
              >
                {tab}
              </button>
            ))}
          </div>

          {activeTab === "My Notes" ? (
            <div className="flex-1 min-h-0 overflow-y-auto p-4">
              {noteAnnotations.length === 0 ? (
                <div className="flex h-full flex-col items-center justify-center gap-3 text-on-surface-variant/60">
                  <ScrollText className="h-6 w-6 opacity-40" />
                  <p className="text-sm font-medium">No highlights yet</p>
                  <p className="text-xs">Pick a color to highlight selected text.</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {noteAnnotations.map((annotation) => {
                    const expanded = expandedAnnotationId === annotation.id
                    const modeLabel = annotation.mode === "source" ? "Source" : "Translated"
                    return (
                      <div
                        key={annotation.id}
                        className="rounded-xl border border-outline-variant/30 bg-surface-container-lowest"
                      >
                        <button
                          type="button"
                          onClick={() => {
                            setExpandedAnnotationId((current) =>
                              current === annotation.id ? null : annotation.id,
                            )
                            onFocusAnnotation(annotation)
                          }}
                          className="flex w-full items-start gap-3 px-3 py-3 text-left"
                        >
                          <span
                            className="mt-1 h-3 w-3 shrink-0 rounded-full"
                            style={{ backgroundColor: getHighlightOverlayColor(annotation.color) }}
                          />
                          <span className="min-w-0 flex-1">
                            <span className="block text-xs text-on-surface-variant/70">{modeLabel}</span>
                            <span className="block truncate text-sm text-on-surface">{annotation.text}</span>
                          </span>
                          <span className="text-xs text-on-surface-variant/70">{expanded ? "Collapse" : "Expand"}</span>
                        </button>

                        {expanded ? (
                          <div className="border-t border-outline-variant/20 px-3 py-3 text-xs text-on-surface-variant space-y-2">
                            {annotation.note ? (
                              <p className="whitespace-pre-wrap text-on-surface">{annotation.note}</p>
                            ) : (
                              <p>No note for this highlight.</p>
                            )}
                          </div>
                        ) : null}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          ) : activeTab !== "Assistant" ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-on-surface-variant/50 gap-4">
              <div className="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center">
                <Bot className="w-6 h-6 opacity-30" />
              </div>
              <p className="text-sm font-medium">Coming Soon</p>
            </div>
          ) : (
            <>
          <div ref={messageListRef} className="flex-1 min-h-0 overflow-y-auto p-4 space-y-4">
            {agentTurns.length === 0 ? (
               <div className="h-full flex flex-col items-center justify-center text-center p-6 text-on-surface-variant/70">
                  <div className="w-16 h-16 rounded-3xl bg-surface-container-highest border border-outline-variant/30 flex items-center justify-center mb-6 shadow-[inset_0_1px_4px_rgba(0,0,0,0.05)]">
                     <Sparkles className="w-8 h-8 text-primary/70" />
                  </div>
                  <h3 className="text-[15px] font-semibold text-on-surface mb-2">Need a prompt idea?</h3>
                  <p className="text-xs text-on-surface-variant/80 mb-6 max-w-[200px]">
                    You can click a card below and let AI analyze this paper.
                  </p>
                  
                  <div className="w-full flex flex-col gap-3 max-w-sm">
                    <button
                      type="button"
                      onClick={() => {
                        onAgentInputChange("Summarize this paper");
                      }}
                      className="w-full text-left p-3 rounded-2xl border border-outline-variant/30 hover:border-primary/40 bg-surface-container-lowest hover:bg-primary/5 hover:shadow-sm transition-all group flex items-start gap-3"
                    >
                      <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center shrink-0 group-hover:bg-primary/20 transition-colors">
                        <ScrollText className="w-4 h-4 text-primary" />
                      </div>
                      <div className="flex flex-col mt-0.5">
                        <span className="text-[13px] font-semibold text-on-surface leading-tight">Summarize this paper</span>
                        <span className="text-[11px] text-on-surface-variant mt-1.5 opacity-80 leading-tight">Extract key goals and contributions</span>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        onAgentInputChange("Explain this highlighted section in detail");
                      }}
                      className="w-full text-left p-3 rounded-2xl border border-outline-variant/30 hover:border-primary/40 bg-surface-container-lowest hover:bg-primary/5 hover:shadow-sm transition-all group flex items-start gap-3"
                    >
                      <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center shrink-0 group-hover:bg-primary/20 transition-colors">
                        <Sparkles className="w-4 h-4 text-primary" />
                      </div>
                      <div className="flex flex-col mt-0.5">
                        <span className="text-[13px] font-semibold text-on-surface leading-tight">Ask about a highlighted section</span>
                        <span className="text-[11px] text-on-surface-variant mt-1.5 opacity-80 leading-tight">Select text and ask for deeper explanation</span>
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() => {
                        onAgentInputChange("What is the core idea of this paper?");
                      }}
                      className="w-full text-left p-3 rounded-2xl border border-outline-variant/30 hover:border-primary/40 bg-surface-container-lowest hover:bg-primary/5 hover:shadow-sm transition-all group flex items-start gap-3"
                    >
                      <div className="w-8 h-8 rounded-xl bg-primary/10 flex items-center justify-center shrink-0 group-hover:bg-primary/20 transition-colors">
                        <Bot className="w-4 h-4 text-primary" />
                      </div>
                      <div className="flex flex-col mt-0.5">
                        <span className="text-[13px] font-semibold text-on-surface leading-tight">What is the core idea?</span>
                        <span className="text-[11px] text-on-surface-variant mt-1.5 opacity-80 leading-tight">Understand the author&apos;s main findings</span>
                      </div>
                    </button>
                  </div>
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
            {agentContext ? (
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
                <div className="text-[13px] leading-relaxed text-on-surface-variant pl-2 border-l-2 border-primary/30 space-y-1">
                  <div className="line-clamp-3 italic opacity-90">{agentContext.text}</div>
                  {agentContext.note && (
                    <div className="text-on-surface font-medium border-t border-outline-variant/10 pt-1 mt-1">
                      {agentContext.note}
                    </div>
                  )}
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
                    "flex items-center gap-1.5 transition-all text-[11px] px-2.5 py-1.5 rounded-lg font-medium active:scale-95",
                    agentMode === "deep_research"
                      ? "bg-primary/10 text-primary shadow-[inset_0_0_0_1px_rgba(var(--color-primary-rgb),0.2)]"
                      : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest"
                  )}
                >
                  <Sparkles className={cn("w-3.5 h-3.5", agentMode === "deep_research" && "animate-pulse")} />
                  Deep Research
                </button>
                <div className="w-px h-3 bg-outline-variant/50 ml-1 mr-1" />
                <button
                  type="button"
                  onClick={() => onExternalSearchChange(!externalSearchEnabled)}
                  className={cn(
                    "flex items-center gap-1.5 transition-all text-[11px] px-2.5 py-1.5 rounded-lg font-medium active:scale-95",
                    externalSearchEnabled
                      ? "bg-primary/10 text-primary shadow-[inset_0_0_0_1px_rgba(var(--color-primary-rgb),0.2)]"
                      : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest"
                  )}
                >
                  <Link2 className={cn("w-3.5 h-3.5", externalSearchEnabled && "animate-pulse")} />
                  Web Search
                </button>
              </div>
            </div>
          </div>
          </>
        )}
        </aside>
      </div>
    </>
  )
}



