import DOMPurify from "dompurify"
import { ChevronDown, ChevronUp, Languages } from "lucide-react"
import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react"
import { useTranslation } from "react-i18next"

import { API_BASE_URL } from "@/api-base"
import { PaperPreviewReader } from "@/components/community/PaperPreviewReader"
import { cn } from "@/lib/utils"
import type {
  CommunityPaper,
  CommunityPaperPreviewResponse,
  CommunityPaperReader,
  CommunityPaperReaderMode,
  StructuredInsightSection,
  StructuredInsightsPayload,
} from "@/types/community"

const SPLIT_STORAGE_KEY = "community-paper-reader-split-ratio-v2"
const DEFAULT_SPLIT_RATIO = 0.65
const MIN_READER_WIDTH = 720
const MIN_SIDEBAR_WIDTH = 260

interface PaperDetailWorkspaceProps {
  paper: CommunityPaper
  preview: CommunityPaperPreviewResponse | null
  readerState: "ready" | "warming" | "unavailable"
  reader: CommunityPaperReader | null
  preferredMode: CommunityPaperReaderMode
  availableModes: CommunityPaperReaderMode[]
  stageLabel: string
  structuredInsights: StructuredInsightsPayload | null
  originalSourceUrl: string | null
  abstractText: string
  canDownload: boolean
  actionError: string | null
  onModeChange: (mode: CommunityPaperReaderMode) => void
}

function isTranslatedHtmlMode(mode: CommunityPaperReaderMode) {
  return mode === "translated" || mode === "translated_html"
}

function isTranslatedPdfMode(mode: CommunityPaperReaderMode) {
  return mode === "translated_pdf"
}

function clampSplitRatio(ratio: number, width: number) {
  if (!Number.isFinite(ratio) || !Number.isFinite(width) || width <= 0) {
    return DEFAULT_SPLIT_RATIO
  }

  const minRatio = MIN_READER_WIDTH / width
  const maxRatio = 1 - MIN_SIDEBAR_WIDTH / width

  return Math.min(Math.max(ratio, minRatio), maxRatio)
}

function getInsightLabel(sectionKey: string, t: (key: string) => string) {
  switch (sectionKey) {
    case "problem":
      return t("community.detail.insights.section.problem")
    case "method":
      return t("community.detail.insights.section.method")
    case "key_idea":
      return t("community.detail.insights.section.keyIdea")
    case "experiment":
      return t("community.detail.insights.section.experiment")
    case "result":
      return t("community.detail.insights.section.result")
    case "limitation":
      return t("community.detail.insights.section.limitation")
    default:
      return t("community.detail.insights.section.fallback")
  }
}

function getInsightContent(section: StructuredInsightSection, mode: CommunityPaperReaderMode) {
  const useZh = mode !== "source"

  return {
    summary: useZh ? section.summary_zh : section.summary_en,
    bullets: useZh ? section.bullets_zh : section.bullets_en,
    body: useZh ? section.body_zh : section.body_en,
  }
}

export function PaperDetailWorkspace({
  paper,
  preview,
  readerState,
  reader,
  preferredMode,
  availableModes,
  stageLabel,
  structuredInsights,
  originalSourceUrl,
  abstractText,
  canDownload,
  actionError,
  onModeChange,
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
  const [activeTab, setActiveTab] = useState<"Insights" | "Notes" | "Comments" | "Similar">("Insights")
  const [expandedInsightKey, setExpandedInsightKey] = useState<string | null>(null)

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

  function handleResizeStart(event: ReactPointerEvent<HTMLDivElement>) {
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

  const sourceHtmlContent =
    preferredMode === "source" && reader?.source?.kind === "source_html"
      ? (reader.source.html_content ?? null)
      : null
  const translatedHtmlContent =
    isTranslatedHtmlMode(preferredMode)
      ? (reader?.translated?.html_content ?? preview?.html_content ?? null)
      : null
  const translatedPreviewAvailable =
    isTranslatedHtmlMode(preferredMode) &&
    (Boolean(preview?.html_content) || reader?.translated?.kind === "preview_html")
  const sourceDocumentUrl = `${API_BASE_URL}/api/papers/${paper.id}/source-pdf`
  const translatedPdfUrl = `${API_BASE_URL}/api/papers/${paper.id}/translated-pdf`
  const sanitizedSourceHtml = useMemo(
    () => (sourceHtmlContent ? DOMPurify.sanitize(sourceHtmlContent) : null),
    [sourceHtmlContent],
  )
  const selectedInsights = structuredInsights?.sections ?? []
  const desktopGridColumns = `${splitRatio}fr 12px ${Math.max(1 - splitRatio, 0.18)}fr`

  return (
    <div
      ref={containerRef}
      data-testid="paper-detail-top-panels"
      className={cn(
        "flex-1 min-h-0 min-w-0 w-full h-full relative",
        isDesktop ? "grid" : "flex flex-col overflow-y-auto",
      )}
      style={isDesktop ? { gridTemplateColumns: desktopGridColumns } : undefined}
    >
      <section
        data-testid="paper-detail-reader-panel"
        className={cn(
          "flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-surface-container-lowest",
          isDesktop ? "" : "border-b border-outline-variant/30 min-h-[50vh]",
        )}
      >
        <div data-testid="paper-reader-scroll-root" className="relative flex-1 overflow-auto bg-surface-container-lowest">
          {preferredMode === "source" ? (
            sourceDocumentUrl ? (
              <iframe
                data-testid="paper-source-pdf-reader"
                title={`${paper.title} PDF`}
                src={sourceDocumentUrl}
                className="h-full w-full border-0 bg-surface-container-lowest"
              />
            ) : sanitizedSourceHtml ? (
              <article
                data-testid="paper-source-reader"
                className="h-full bg-surface-container-lowest px-6 py-6 text-on-surface sm:px-8 lg:px-10 lg:py-8 [&_article]:mx-auto [&_article]:max-w-[1040px] [&_article]:space-y-6 [&_figcaption]:text-sm [&_figcaption]:leading-6 [&_figcaption]:text-on-surface-variant [&_figure]:my-8 [&_figure]:overflow-x-auto [&_h1]:mt-8 [&_h1]:text-4xl [&_h1]:font-semibold [&_h1]:tracking-[-0.04em] [&_h2]:mt-10 [&_h2]:text-[1.85rem] [&_h2]:font-semibold [&_h2]:tracking-[-0.03em] [&_h3]:mt-8 [&_h3]:text-[1.35rem] [&_h3]:font-semibold [&_li]:leading-8 [&_ol]:space-y-3 [&_p]:text-[17px] [&_p]:leading-8"
                dangerouslySetInnerHTML={{ __html: sanitizedSourceHtml }}
              />
            ) : (
              <article data-testid="paper-source-reader" className="flex h-full flex-col gap-4 px-10 py-8">
                {originalSourceUrl ? (
                  <a
                    href={originalSourceUrl}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-2 text-sm text-primary underline-offset-4 hover:underline"
                  >
                    {t("community.detail.originalSource")}
                  </a>
                ) : null}
              </article>
            )
          ) : isTranslatedHtmlMode(preferredMode) && readerState === "warming" ? (
            <div className="h-full bg-surface-container-lowest">
              <PaperPreviewReader paperId={paper.id} initialPreview={null} readerState={readerState} />
            </div>
          ) : isTranslatedHtmlMode(preferredMode) && (translatedPreviewAvailable || translatedHtmlContent) ? (
            <div className="h-full bg-surface-container-lowest">
              <PaperPreviewReader paperId={paper.id} initialPreview={preview} readerState={readerState} />
            </div>
          ) : isTranslatedPdfMode(preferredMode) && canDownload ? (
            <iframe
              data-testid="paper-translated-pdf-reader"
              title={`${paper.title} Translated PDF`}
              src={translatedPdfUrl}
              className="h-[720px] w-full border-0 bg-surface-container-lowest"
            />
          ) : (
            <article className="flex h-full flex-col gap-4 px-10 py-8">
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
          "flex min-h-0 min-w-0 flex-col overflow-hidden bg-surface-container-low relative shrink-0",
          isDesktop ? "h-full" : "min-h-[500px]",
        )}
      >
        <div data-testid="paper-detail-insights-panel" className="contents" />
        <div className="flex bg-surface-container-lowest border-b border-outline-variant/30 shrink-0 px-2 pt-2 gap-1 overflow-hidden no-scrollbar">
          {(["Insights", "Notes", "Comments", "Similar"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={cn(
                "px-4 py-2.5 text-sm font-medium border-b-2 transition-colors relative -bottom-[1px] whitespace-nowrap outline-none",
                activeTab === tab
                  ? "border-primary text-primary"
                  : "border-transparent text-on-surface-variant hover:text-on-surface hover:border-outline-variant/50",
              )}
            >
              {tab}
            </button>
          ))}
        </div>

        {activeTab === "Insights" ? (
          <div className="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
            <div className="rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-primary">
                {t("community.detail.insightsEyebrow")}
              </p>
              <h2 className="mt-2 text-base font-semibold text-on-surface">
                {t("community.detail.insightsTitle")}
              </h2>
              <p className="mt-2 text-xs leading-6 text-on-surface-variant">
                {t("community.detail.insightsDescription")}
              </p>
              <div className="mt-3 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-on-surface-variant/70">
                <span>{stageLabel}</span>
                <span aria-hidden="true">|</span>
                <button
                  type="button"
                  data-testid="paper-detail-mode-source"
                  aria-pressed={preferredMode === "source"}
                  onClick={() => onModeChange("source")}
                  className={cn(
                    "transition-colors",
                    preferredMode === "source" ? "text-primary" : "hover:text-on-surface",
                  )}
                >
                  {t("community.detail.mode.source")}
                </button>
                <span>/</span>
                <button
                  type="button"
                  data-testid="paper-detail-mode-translated-html"
                  disabled={!availableModes.includes("translated_html")}
                  aria-pressed={preferredMode === "translated_html"}
                  onClick={() => onModeChange("translated_html")}
                  className={cn(
                    "transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
                    preferredMode === "translated_html" ? "text-primary" : "hover:text-on-surface",
                  )}
                >
                  {t("community.detail.mode.translatedHtml")}
                </button>
                <span>/</span>
                <button
                  type="button"
                  data-testid="paper-detail-mode-translated-pdf"
                  disabled={!availableModes.includes("translated_pdf")}
                  aria-pressed={preferredMode === "translated_pdf"}
                  onClick={() => onModeChange("translated_pdf")}
                  className={cn(
                    "transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
                    preferredMode === "translated_pdf" ? "text-primary" : "hover:text-on-surface",
                  )}
                >
                  {t("community.detail.mode.translatedPdf")}
                </button>
              </div>
            </div>

            {actionError ? (
              <div className="rounded-xl border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
                {actionError}
              </div>
            ) : null}

            {structuredInsights?.state === "processing" || structuredInsights?.state === "queued" ? (
              <div className="rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-4">
                <h3 className="text-sm font-semibold text-on-surface">{t("community.detail.insightsPendingTitle")}</h3>
                <p className="mt-2 text-xs leading-6 text-on-surface-variant">
                  {t("community.detail.insightsPendingDescription")}
                </p>
              </div>
            ) : selectedInsights.length > 0 ? (
              selectedInsights.map((section) => {
                const content = getInsightContent(section, preferredMode)
                const expanded = expandedInsightKey === section.section_key || expandedInsightKey === null

                return (
                  <div
                    key={section.section_key}
                    className="rounded-xl border border-outline-variant/30 bg-surface-container-lowest"
                  >
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedInsightKey((current) =>
                          current === section.section_key ? "" : section.section_key,
                        )
                      }
                      className="flex w-full items-start justify-between gap-3 px-4 py-4 text-left"
                    >
                      <span className="text-[13px] font-semibold text-on-surface">
                        {getInsightLabel(section.section_key, t)}
                      </span>
                      {expanded ? (
                        <ChevronUp className="h-4 w-4 text-on-surface-variant" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-on-surface-variant" />
                      )}
                    </button>

                    {expanded ? (
                      <div className="border-t border-outline-variant/20 px-4 py-4 text-sm text-on-surface-variant space-y-3">
                        {content.summary ? <p className="text-on-surface whitespace-pre-wrap">{content.summary}</p> : null}
                        {content.bullets?.length ? (
                          <ul className="space-y-2 pl-5">
                            {content.bullets.map((bullet, index) => (
                              <li key={`${section.section_key}-${index}`} className="list-disc">
                                {bullet}
                              </li>
                            ))}
                          </ul>
                        ) : null}
                        {content.body ? <p className="whitespace-pre-wrap">{content.body}</p> : null}
                        {!content.summary && !content.body && !content.bullets?.length ? (
                          <p>{t("community.detail.insights.languagePending")}</p>
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                )
              })
            ) : (
              <div className="rounded-xl border border-outline-variant/30 bg-surface-container-lowest p-4">
                <h3 className="text-sm font-semibold text-on-surface">{t("community.detail.insightsEmptyTitle")}</h3>
                <p className="mt-2 text-xs leading-6 text-on-surface-variant">
                  {t("community.detail.insightsEmptyDescription")}
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-on-surface-variant/50 gap-4">
            <div className="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center">
              <Languages className="w-6 h-6 opacity-30" />
            </div>
            <p className="text-sm font-medium">Coming Soon</p>
          </div>
        )}
      </aside>
    </div>
  )
}
