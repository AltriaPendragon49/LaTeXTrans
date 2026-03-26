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
    <div className="mt-4 space-y-3">
      <style>{`::highlight(${READER_SELECTION_HIGHLIGHT_NAME}) { background-color: rgba(250, 204, 21, 0.45); }`}</style>
      <div className="rounded-[22px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] px-4 py-3">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-2.5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="rounded-full bg-[var(--shell-pill)] px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-[var(--shell-heading)]">
                {stageLabel}
              </Badge>
              <div
                className="inline-flex items-center gap-1 rounded-full border border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-1"
                data-testid="paper-detail-mode-switch"
              >
                <button
                  type="button"
                  data-testid="paper-detail-mode-source"
                  aria-pressed={preferredMode === "source"}
                  disabled={!sourceAvailable}
                  onClick={() => onModeChange("source")}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium transition",
                    preferredMode === "source"
                      ? "bg-[var(--shell-heading)] text-[var(--shell-surface)]"
                      : "text-[var(--shell-text-soft)] hover:bg-[var(--shell-pill)]",
                    !sourceAvailable && "cursor-not-allowed opacity-45",
                  )}
                >
                  {t("community.detail.mode.source")}
                </button>
                <button
                  type="button"
                  data-testid="paper-detail-mode-translated"
                  aria-pressed={preferredMode === "translated"}
                  disabled={!translatedAvailable}
                  onClick={() => onModeChange("translated")}
                  className={cn(
                    "rounded-full px-3 py-1.5 text-xs font-medium transition",
                    preferredMode === "translated"
                      ? "bg-[var(--shell-heading)] text-[var(--shell-surface)]"
                      : "text-[var(--shell-text-soft)] hover:bg-[var(--shell-pill)]",
                    !translatedAvailable && "cursor-not-allowed opacity-45",
                  )}
                >
                  {t("community.detail.mode.translated")}
                </button>
              </div>
              <Badge variant="outline" className="rounded-full border-[color:var(--shell-border)] bg-transparent">
                {t("community.detail.latestAsset")}
              </Badge>
            </div>
            {softBanner ? <p className="text-sm text-[var(--shell-heading)]">{softBanner}</p> : null}
            {canLeaveHint ? (
              <p className="text-sm text-[var(--shell-text-soft)]">{canLeaveHint}</p>
            ) : null}
            {actionError ? (
              <p className="text-sm text-rose-500">{actionError}</p>
            ) : null}
          </div>

          <div className="flex flex-wrap gap-2 xl:max-w-[420px] xl:justify-end">
            <Button
              type="button"
              disabled={!canTranslate}
              onClick={onTranslate}
              variant="outline"
              className="h-10 rounded-[16px] border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-4 text-[var(--shell-heading)]"
            >
              <Languages className="h-4 w-4" />
              <span>{t("community.actions.translate")}</span>
            </Button>
            <Button
              type="button"
              disabled={!canViewProgress}
              onClick={onViewProgress}
              variant="outline"
              className="h-10 rounded-[16px] border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-4 text-[var(--shell-heading)]"
            >
              <Timer className="h-4 w-4" />
              <span>{t("community.actions.viewProgress")}</span>
            </Button>
            <Button
              type="button"
              onClick={onPreview}
              variant="outline"
              className="h-10 rounded-[16px] border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-4 text-[var(--shell-heading)]"
            >
              <Eye className="h-4 w-4" />
              <span>{t("community.actions.preview")}</span>
            </Button>
            <Button
              type="button"
              disabled={!canDownload}
              onClick={onDownload}
              variant="outline"
              className="h-10 rounded-[16px] border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-4 text-[var(--shell-heading)]"
            >
              <Download className="h-4 w-4" />
              <span>{t("community.actions.download")}</span>
            </Button>
          </div>
        </div>
      </div>

      <div
        ref={containerRef}
        data-testid="paper-detail-top-panels"
        className={cn("grid gap-3", isDesktop ? "gap-0" : "")}
        style={isDesktop ? { gridTemplateColumns: desktopGridColumns } : undefined}
      >
        <section
          data-testid="paper-detail-reader-panel"
          className={cn(
            "flex h-[calc(140dvh-160px)] max-h-[calc(140dvh-160px)] min-w-0 flex-col overflow-hidden rounded-[26px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] shadow-none transition [&_[data-reader-anchor-active='true']]:rounded-md [&_[data-reader-anchor-active='true']]:ring-2 [&_[data-reader-anchor-active='true']]:ring-sky-400/70 [&_[data-reader-anchor-active='true']]:ring-offset-2 [&_[data-reader-anchor-active='true']]:ring-offset-white [&_[data-reader-selection-active='true']]:rounded-sm [&_[data-reader-selection-active='true']]:bg-amber-200/60 [&_[data-reader-selection-active='true']]:shadow-[inset_0_0_0_1px_rgba(245,158,11,0.55)]",
            readerHighlight ? "ring-2 ring-sky-400/60" : "",
          )}
        >
          <div className="flex items-center justify-between border-b border-[color:var(--shell-border)] px-4 py-2.5">
            <div className="flex items-center gap-2 text-sm font-medium text-[var(--shell-heading)]">
              <ScrollText className="h-4 w-4 text-[var(--shell-icon)]" />
              {t("community.detail.workspaceTitle")}
            </div>
            {sourceExternalLink ? (
              <a
                href={sourceExternalLink}
                target="_blank"
                rel="noreferrer noopener"
                className="inline-flex items-center gap-2 text-xs text-[var(--shell-text-soft)] transition hover:text-[var(--shell-heading)]"
              >
                <Link2 className="h-3.5 w-3.5" />
                {t("community.detail.originalSource")}
              </a>
            ) : null}
          </div>

          <div className="min-h-0 flex-1 bg-[var(--shell-bg)]">
            {preferredMode === "source" ? (
              sourceHtmlContent ? (
                <article
                  data-testid="paper-source-reader"
                  className="h-full overflow-y-auto bg-white px-6 py-6 text-slate-900 sm:px-8 lg:px-10 lg:py-8 [&_article]:mx-auto [&_article]:max-w-[1040px] [&_article]:space-y-6 [&_figcaption]:text-sm [&_figcaption]:leading-6 [&_figcaption]:text-slate-500 [&_figure]:my-8 [&_figure]:overflow-x-auto [&_h1]:mt-8 [&_h1]:text-4xl [&_h1]:font-semibold [&_h1]:tracking-[-0.04em] [&_h2]:mt-10 [&_h2]:text-[1.85rem] [&_h2]:font-semibold [&_h2]:tracking-[-0.03em] [&_h3]:mt-8 [&_h3]:text-[1.35rem] [&_h3]:font-semibold [&_li]:leading-8 [&_ol]:space-y-3 [&_p]:text-[17px] [&_p]:leading-8 [&_pre]:overflow-x-auto [&_pre]:rounded-2xl [&_pre]:bg-slate-950 [&_pre]:p-4 [&_pre]:text-sm [&_pre]:text-slate-100 [&_table]:w-full [&_table]:overflow-x-auto [&_table]:text-sm [&_td]:border [&_td]:border-slate-200 [&_td]:px-3 [&_td]:py-2 [&_th]:border [&_th]:border-slate-200 [&_th]:bg-slate-50 [&_th]:px-3 [&_th]:py-2 [&_ul]:space-y-3"
                  dangerouslySetInnerHTML={{ __html: sourceHtmlContent }}
                />
              ) : sourceDocumentUrl ? (
                <iframe
                  data-testid="paper-source-pdf-reader"
                  title={`${paper.title} PDF`}
                  src={sourceDocumentUrl}
                  className="h-full w-full border-0 bg-white"
                />
              ) : (
                <article
                  data-testid="paper-source-reader"
                  className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto px-10 py-8"
                >
                  <h2 className="text-2xl font-semibold text-[var(--shell-heading)]">{paper.title}</h2>
                  <p className="max-w-4xl text-base leading-8 text-[var(--shell-text-soft)]">{abstractText}</p>
                  {originalSourceUrl ? (
                    <a
                      href={originalSourceUrl}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="inline-flex items-center gap-2 text-sm text-sky-600 underline-offset-4 hover:underline dark:text-sky-300"
                    >
                      <Link2 className="h-4 w-4" />
                      {t("community.detail.originalSource")}
                    </a>
                  ) : null}
                </article>
              )
            ) : preferredMode === "translated" && readerState === "warming" ? (
              <div className="h-full p-3">
                <PaperPreviewReader ref={previewRef} paperId={paper.id} initialPreview={null} readerState={readerState} />
              </div>
            ) : translatedPreviewAvailable ? (
              <div className="h-full p-3">
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
                  className="h-full overflow-y-auto bg-white px-6 py-6 text-slate-900 sm:px-8 lg:px-10 lg:py-8 [&_article]:mx-auto [&_article]:max-w-[1040px] [&_article]:space-y-6 [&_figcaption]:text-sm [&_figcaption]:leading-6 [&_figcaption]:text-slate-500 [&_figure]:my-8 [&_figure]:overflow-x-auto [&_h1]:mt-8 [&_h1]:text-4xl [&_h1]:font-semibold [&_h1]:tracking-[-0.04em] [&_h2]:mt-10 [&_h2]:text-[1.85rem] [&_h2]:font-semibold [&_h2]:tracking-[-0.03em] [&_h3]:mt-8 [&_h3]:text-[1.35rem] [&_h3]:font-semibold [&_li]:leading-8 [&_ol]:space-y-3 [&_p]:text-[17px] [&_p]:leading-8 [&_pre]:overflow-x-auto [&_pre]:rounded-2xl [&_pre]:bg-slate-950 [&_pre]:p-4 [&_pre]:text-sm [&_pre]:text-slate-100 [&_table]:w-full [&_table]:overflow-x-auto [&_table]:text-sm [&_td]:border [&_td]:border-slate-200 [&_td]:px-3 [&_td]:py-2 [&_th]:border [&_th]:border-slate-200 [&_th]:bg-slate-50 [&_th]:px-3 [&_th]:py-2 [&_ul]:space-y-3"
                  dangerouslySetInnerHTML={{ __html: translatedHtmlContent }}
                />
              )
            ) : translatedPdfFallback?.kind === "translated_pdf" ? (
              <article
                data-testid="paper-translated-pdf-fallback"
                className="flex h-full min-h-0 flex-col items-center justify-center gap-4 px-10 py-8 text-center"
              >
                <h2 className="text-2xl font-semibold text-[var(--shell-heading)]">
                  {t("community.card.assetType.translated_pdf")}
                </h2>
                <p className="max-w-2xl text-base leading-7 text-[var(--shell-text-soft)]">{stageLabel}</p>
                <Button type="button" onClick={onDownload} className="rounded-full">
                  <Download className="h-4 w-4" />
                  {t("community.actions.download")}
                </Button>
              </article>
            ) : (
              <article
                data-testid="paper-translated-reader"
                className="flex h-full min-h-0 flex-col gap-4 overflow-y-auto px-10 py-8"
              >
                <h2 className="text-2xl font-semibold text-[var(--shell-heading)]">{paper.title}</h2>
                <p className="max-w-4xl text-base leading-8 text-[var(--shell-text-soft)]">{abstractText}</p>
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
            className="group flex cursor-col-resize items-stretch justify-center"
          >
            <div className="mx-auto flex h-full w-full items-center justify-center">
              <div className="h-20 w-[3px] rounded-full bg-[var(--shell-border)] transition group-hover:bg-[var(--shell-heading)]" />
            </div>
          </div>
        ) : null}

        <aside
          data-testid="paper-detail-agent-panel"
          className={cn(
            "flex flex-col overflow-hidden rounded-[28px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] shadow-none",
            isDesktop
              ? "min-w-[320px] self-start h-[calc(100dvh-160px)] max-h-[calc(100dvh-160px)] min-h-[560px]"
              : "min-h-[560px]",
          )}
        >
          <div className="flex items-center gap-2 border-b border-[color:var(--shell-border)] px-5 py-3 text-sm font-medium text-[var(--shell-heading)]">
            <Languages className="h-4 w-4 text-[var(--shell-icon)]" />
            {t("community.detail.agentWorkspaceTitle")}
          </div>
          <div ref={messageListRef} className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-4 py-4">
            {agentTurns.map((turn) => {
              const assistantRun = turn.role === "assistant" ? turn.run : null
              const citations = assistantRun?.citations ?? []
              const toolTrace = assistantRun?.tool_trace ?? []
              return (
                <div
                  key={turn.id}
                  className={cn(
                    "rounded-[20px] border px-4 py-3",
                    turn.role === "user"
                      ? "border-[color:var(--shell-accent)] bg-[color:color-mix(in_srgb,var(--shell-accent)_16%,white_84%)]"
                      : "border-[color:var(--shell-border)] bg-[var(--shell-surface)]",
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-[11px] uppercase tracking-[0.18em] text-[var(--shell-text-muted)]">
                      {turn.role === "user" ? t("community.conversation.userLabel") : t("community.conversation.agentLabel")}
                    </p>
                    <p className="text-[11px] text-[var(--shell-text-muted)]">
                      {formatConversationTimestamp(turn.created_at)}
                    </p>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-[var(--shell-text-soft)]">
                    {turn.content}
                  </p>

                  {citations.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {citations.map((citation) => (
                        <button
                          key={citation.id}
                          type="button"
                          onClick={() => void onCitationOpen(citation)}
                          className="inline-flex items-center gap-2 rounded-full border border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 py-2 text-xs text-[var(--shell-heading)] transition hover:bg-[var(--shell-pill-hover)]"
                        >
                          <span className="truncate">{citation.title}</span>
                          <ArrowUpRight className="h-3.5 w-3.5" />
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
                            "flex items-start gap-3 rounded-[16px] border px-3 py-2 text-xs",
                            getTraceStatusClass(entry.status),
                          )}
                        >
                          {entry.kind === "reasoning" ? (
                            <Sparkles className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                          ) : (
                            <Bot className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                          )}
                          <div className="min-w-0">
                            <div className="font-medium">{entry.label}</div>
                            {entry.detail ? (
                              <div className="mt-1 text-[11px] text-current/80">{entry.detail}</div>
                            ) : null}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              )
            })}

            {agentBusy ? (
              <div className="flex items-center gap-2 rounded-2xl border border-[color:var(--shell-border)] bg-[var(--shell-surface)] px-4 py-3 text-sm text-[var(--shell-text-soft)]">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>{t("community.conversation.running")}</span>
              </div>
            ) : null}

            {agentError ? (
              <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-700 dark:text-rose-200">
                {agentError}
              </div>
            ) : null}
          </div>

          <div className="border-t border-[color:var(--shell-border)] px-4 py-4">
            {readerSelection ? (
              <div className="mb-3 rounded-2xl border border-[color:var(--shell-border)] bg-[var(--shell-surface)] px-3 py-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs uppercase tracking-[0.16em] text-[var(--shell-text-muted)]">
                    {t("community.detail.selectionContextTitle")}
                  </p>
                  <button
                    type="button"
                    onClick={onSelectionClear}
                    className="text-xs text-[var(--shell-text-soft)] underline-offset-2 hover:underline"
                  >
                    {t("common.actions.cancel")}
                  </button>
                </div>
                <p className="mt-2 line-clamp-4 whitespace-pre-wrap text-sm leading-6 text-[var(--shell-text-soft)]">
                  {readerSelection.text}
                </p>
              </div>
            ) : null}

            {preferredMode === "source" ? (
              <div className="mb-3 flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant="outline"
                  className="rounded-full"
                  disabled={agentBusy}
                  onClick={onQuickExplain}
                >
                  {t("community.detail.quickExplain")}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  className="rounded-full"
                  disabled={agentBusy}
                  onClick={onQuickSummary}
                >
                  {t("community.detail.quickSummary")}
                </Button>
              </div>
            ) : null}

            <form onSubmit={handleAgentSubmit} className="space-y-3">
              <label htmlFor="paper-detail-agent-input" className="sr-only">
                {t("community.agent.aria")}
              </label>
              <textarea
                id="paper-detail-agent-input"
                aria-label={t("community.agent.aria")}
                value={agentInput}
                onChange={(event) => onAgentInputChange(event.target.value)}
                placeholder={t("community.agent.placeholder")}
                rows={3}
                className="min-h-[96px] w-full resize-none rounded-[20px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] px-3 py-2 text-sm leading-7 text-[var(--shell-heading)] outline-none placeholder:text-[var(--shell-text-muted)]"
              />

              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-col gap-2">
                  <div
                    role="group"
                    aria-label={t("community.agent.mode.aria")}
                    className="inline-flex w-fit items-center gap-1 rounded-full border border-[color:var(--shell-border)] bg-[var(--shell-pill)] p-1"
                  >
                    <button
                      type="button"
                      aria-pressed={agentMode === "chat"}
                      onClick={() => onAgentModeChange("chat")}
                      className={cn(
                        "rounded-full px-3 py-1 text-xs font-medium transition",
                        agentMode === "chat"
                          ? "bg-[var(--shell-accent)] text-[var(--shell-accent-foreground)]"
                          : "text-[var(--shell-text-soft)] hover:text-[var(--shell-heading)]",
                      )}
                    >
                      {t("community.agent.mode.chat")}
                    </button>
                    <button
                      type="button"
                      aria-pressed={agentMode === "deep_research"}
                      onClick={() => onAgentModeChange("deep_research")}
                      className={cn(
                        "rounded-full px-3 py-1 text-xs font-medium transition",
                        agentMode === "deep_research"
                          ? "bg-[var(--shell-accent)] text-[var(--shell-accent-foreground)]"
                          : "text-[var(--shell-text-soft)] hover:text-[var(--shell-heading)]",
                      )}
                    >
                      {t("community.agent.mode.deepResearch")}
                    </button>
                  </div>
                  <label className="inline-flex items-center gap-2 text-xs text-[var(--shell-text-soft)]">
                    <Switch
                      checked={externalSearchEnabled}
                      onCheckedChange={onExternalSearchChange}
                      aria-label={t("community.agent.externalSearch.label")}
                    />
                    <span>{t("community.agent.externalSearch.label")}</span>
                  </label>
                </div>

                <Button
                  type="submit"
                  disabled={agentBusy || !agentInput.trim()}
                  className="h-10 rounded-full bg-[var(--shell-accent)] px-4 text-[var(--shell-accent-foreground)] hover:bg-[var(--shell-accent-hover)]"
                >
                  {t("community.agent.run")}
                  <ArrowUpRight className="h-4 w-4" />
                </Button>
              </div>
            </form>
          </div>
        </aside>
      </div>

    </div>
  )
}
