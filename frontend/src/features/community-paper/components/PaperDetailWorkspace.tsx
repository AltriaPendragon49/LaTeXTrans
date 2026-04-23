import DOMPurify from "dompurify"
import { ChevronUp } from "lucide-react"
import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import { getCommunityPaperSimilar } from "@/features/community-paper/services/community-paper-api"
import { stripLeadingDuplicatePaperHeaderHtml } from "@/lib/paper-reader-html"
import { cn } from "@/lib/utils"
import { Button } from "@/ui/button/Button"
import { DisclosureCard } from "@/ui/disclosure-card/DisclosureCard"
import { NoticeBanner } from "@/ui/notice-banner/NoticeBanner"
import { StatePanel } from "@/ui/state-panel/StatePanel"
import { EditorialTabs, EditorialTabsList, EditorialTabsTrigger } from "@/ui/tabs/EditorialTabs"
import type {
  CommunityPaper,
  CommunityPaperPreviewResponse,
  CommunityPaperReader,
  CommunityPaperReaderMode,
  CommunityPaperSimilarItem,
  StructuredInsightBlock,
  StructuredInsightSection,
  StructuredInsightSectionKey,
  StructuredInsightsPayload,
} from "@/types/community"

const SPLIT_STORAGE_KEY = "community-paper-reader-split-ratio-v2"
const DEFAULT_SPLIT_RATIO = 0.8
const MIN_READER_WIDTH = 720
const MIN_SIDEBAR_WIDTH = 260
const GUIDE_SECTION_ORDER = [
  "problem",
  "solution",
  "innovation",
  "experiment",
  "future",
] as const

interface PaperDetailWorkspaceProps {
  paper: CommunityPaper
  preview: CommunityPaperPreviewResponse | null
  readerState: "ready" | "warming" | "unavailable"
  reader: CommunityPaperReader | null
  preferredMode: CommunityPaperReaderMode
  structuredInsights: StructuredInsightsPayload | null
  originalSourceUrl: string | null
  abstractText: string
  canDownload: boolean
  actionError: string | null
  mobileAnalysisJumpRequest?: number
}

function isTranslatedPdfMode(mode: CommunityPaperReaderMode) {
  return mode === "translated" || mode === "translated_pdf"
}

function isBilingualCompareMode(mode: CommunityPaperReaderMode) {
  return mode === "bilingual_compare"
}

type PdfViewerMode = "single" | "bilingual"

function buildPdfViewerUrl(url: string, mode: PdfViewerMode = "single") {
  const view = mode === "bilingual" ? "FitH" : "FitH"
  const viewerParams = `page=1&view=${view}&pagemode=none&toolbar=0&navpanes=0&scrollbar=0`
  return url.includes("#") ? `${url}&${viewerParams}` : `${url}#${viewerParams}`
}

function resolvePdfDocumentUrl(
  fallbackUrl: string,
  resource: { kind?: string | null; url?: string | null } | null | undefined,
  expectedKind: "source_pdf" | "translated_pdf",
) {
  const candidateUrl = String(resource?.url || "").trim()
  if ((resource?.kind ?? null) !== expectedKind || !candidateUrl) {
    return fallbackUrl
  }
  if (candidateUrl.startsWith("http://") || candidateUrl.startsWith("https://")) {
    return candidateUrl
  }
  if (candidateUrl.startsWith("/")) {
    return `${API_BASE_URL}${candidateUrl}`
  }
  return fallbackUrl
}

function clampSplitRatio(ratio: number, width: number) {
  if (!Number.isFinite(ratio) || !Number.isFinite(width) || width <= 0) {
    return DEFAULT_SPLIT_RATIO
  }

  const minRatio = MIN_READER_WIDTH / width
  const maxRatio = 1 - MIN_SIDEBAR_WIDTH / width

  return Math.min(Math.max(ratio, minRatio), maxRatio)
}

function isGuideSectionKey(sectionKey: string): sectionKey is StructuredInsightSectionKey {
  return GUIDE_SECTION_ORDER.includes(sectionKey as StructuredInsightSectionKey)
}

function getInsightLabel(sectionKey: StructuredInsightSectionKey, t: (key: string) => string) {
  switch (sectionKey) {
    case "problem":
      return t("community.detail.insights.section.problem")
    case "solution":
      return t("community.detail.insights.section.solution")
    case "innovation":
      return t("community.detail.insights.section.innovation")
    case "experiment":
      return t("community.detail.insights.section.experiment")
    case "future":
      return t("community.detail.insights.section.future")
  }
}

interface ParsedInsightContent {
  summary: string | null
  sections: Array<{
    title: string
    body: string
  }>
  paragraphs: string[]
}

const INLINE_INSIGHT_SECTION_TITLES = [
  "问题本质",
  "现有方法的局限",
  "现有方法的关键不足",
  "为什么重要",
  "研究动机",
  "核心难点",
  "核心思路",
  "方法整体",
  "关键流程",
  "整体流程",
  "模块协同",
  "方法机制",
  "Pipeline",
  "pipeline",
  "关键创新点",
  "本质差异",
  "为什么不一样",
  "新意所在",
  "差异来源",
  "核心指标",
  "对比结果",
  "实验结论",
  "主要结论",
  "评估方式",
  "实验设置",
  "当前局限",
  "真实局限",
  "潜在局限",
  "改进方向",
  "扩展方向",
  "研究启发",
] as const

const INLINE_INSIGHT_SECTION_TITLE_SET = new Set<string>(INLINE_INSIGHT_SECTION_TITLES)

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

function normalizeInsightTitleLine(line: string) {
  const normalized = line
    .replace(/^[#*\-\s>\d.)]+/, "")
    .replace(/[：:]\s*$/, "")
    .trim()

  return INLINE_INSIGHT_SECTION_TITLE_SET.has(normalized) ? normalized : null
}

function extractHeuristicTitledBlock(block: string) {
  const lines = block
    .split(/\r?\n/g)
    .map((line) => line.trim())
    .filter(Boolean)

  if (lines.length < 2) {
    return null
  }

  const firstLine = lines[0]
  if (firstLine.length > 14 || /[.?!:。！？：]/.test(firstLine)) {
    return null
  }

  return {
    lead: "",
    sections: [
      {
        title: firstLine,
        body: lines.slice(1).join("\n"),
      },
    ],
  }
}

function normalizeStructuredInsightBlock(block: StructuredInsightBlock | null | undefined) {
  const heading = block?.heading?.trim()
  const content = block?.content?.trim()
  if (!heading || !content) {
    return null
  }
  return {
    title: heading,
    body: content,
  }
}

function resolveInsightContent(section: StructuredInsightSection): ParsedInsightContent | null {
  const normalizedBlocks = (section.blocks ?? [])
    .map((block) => normalizeStructuredInsightBlock(block))
    .filter((block): block is NonNullable<ReturnType<typeof normalizeStructuredInsightBlock>> => Boolean(block))
  const normalizedSummary = section.summary?.trim() ?? null

  if (normalizedSummary || normalizedBlocks.length > 0) {
    return {
      summary: normalizedSummary,
      sections: normalizedBlocks,
      paragraphs: [],
    }
  }

  const fallbackContent = section.content?.trim() || section.raw_content?.trim() || ""
  return fallbackContent ? parseInsightContent(fallbackContent) : null
}

function extractLineTitledSections(block: string) {
  const lines = block
    .split(/\r?\n/g)
    .map((line) => line.trim())
    .filter(Boolean)

  if (lines.length < 2) {
    return null
  }

  const sections: ParsedInsightContent["sections"] = []
  const introLines: string[] = []
  let currentTitle: string | null = null
  let currentBody: string[] = []

  const pushCurrentSection = () => {
    if (!currentTitle) {
      return
    }

    const body = currentBody.join("\n").trim()
    if (body) {
      sections.push({ title: currentTitle, body })
    }

    currentTitle = null
    currentBody = []
  }

  for (const line of lines) {
    const knownTitle = normalizeInsightTitleLine(line)
    if (knownTitle) {
      pushCurrentSection()
      currentTitle = knownTitle
      continue
    }

    if (currentTitle) {
      currentBody.push(line)
    } else {
      introLines.push(line)
    }
  }

  pushCurrentSection()

  if (sections.length === 0) {
    return null
  }

  return {
    lead: introLines.join("\n").trim(),
    sections,
  }
}

function extractInlineTitledSections(block: string) {
  const titlePattern = INLINE_INSIGHT_SECTION_TITLES
    .slice()
    .sort((left, right) => right.length - left.length)
    .map(escapeRegExp)
    .join("|")
  const matcher = new RegExp(`(?:^|\\s)(${titlePattern})(?:\\s*[：:]|\\s+)`, "g")
  const matches = Array.from(block.matchAll(matcher))

  if (matches.length === 0) {
    return null
  }

  const sections: ParsedInsightContent["sections"] = []
  const lead = block.slice(0, matches[0].index ?? 0).trim()

  for (let index = 0; index < matches.length; index += 1) {
    const currentMatch = matches[index]
    const nextMatch = matches[index + 1]
    const title = currentMatch[1]?.trim() ?? ""
    const bodyStart = (currentMatch.index ?? 0) + currentMatch[0].length
    const bodyEnd = nextMatch?.index ?? block.length
    const body = block.slice(bodyStart, bodyEnd).trim()

    if (title && body) {
      sections.push({ title, body })
    }
  }

  if (sections.length === 0) {
    return null
  }

  return { lead, sections }
}

function parseInsightContent(content: string): ParsedInsightContent {
  const normalized = content
    .split(/\r?\n\s*\r?\n/g)
    .map((block) => block.trim())
    .filter(Boolean)

  if (normalized.length === 0) {
    return { summary: null, sections: [], paragraphs: [] }
  }

  const [summaryBlock, ...restBlocks] = normalized
  const sections: ParsedInsightContent["sections"] = []
  const paragraphs: string[] = []
  let summary = summaryBlock || null

  const structuredSummaryBlock =
    extractLineTitledSections(summaryBlock) ??
    extractHeuristicTitledBlock(summaryBlock) ??
    extractInlineTitledSections(summaryBlock)

  if (structuredSummaryBlock) {
    summary = structuredSummaryBlock.lead || null
    sections.push(...structuredSummaryBlock.sections)
  }

  for (const block of restBlocks) {
    const lines = block
      .split(/\r?\n/g)
      .map((line) => line.trim())
      .filter(Boolean)

    if (
      lines.length >= 2 &&
      lines[0].length <= 14 &&
      !/[。！？：:；;]/.test(lines[0])
    ) {
      sections.push({
        title: lines[0],
        body: lines.slice(1).join("\n"),
      })
      continue
    }

    const inlineTitledContent = extractInlineTitledSections(block)
    if (inlineTitledContent) {
      if (inlineTitledContent.lead) {
        paragraphs.push(inlineTitledContent.lead)
      }

      sections.push(...inlineTitledContent.sections)
      continue
    }

    paragraphs.push(block)
  }

  return {
    summary,
    sections,
    paragraphs,
  }
}

export function PaperDetailWorkspace({
  paper,
  preview: _preview,
  readerState,
  reader,
  preferredMode,
  structuredInsights,
  originalSourceUrl,
  abstractText,
  canDownload,
  actionError,
  mobileAnalysisJumpRequest = 0,
}: PaperDetailWorkspaceProps) {
  void _preview
  void readerState
  const { t } = useTranslation()
  const containerRef = useRef<HTMLDivElement | null>(null)
  const readerPanelRef = useRef<HTMLElement | null>(null)
  const autoFocusedPaperIdRef = useRef<string | null>(null)
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
  const [activeTab, setActiveTab] = useState<"insights" | "similar">("insights")
  const [expandedInsightKey, setExpandedInsightKey] = useState<string>("")
  const [similarState, setSimilarState] = useState<"idle" | "loading" | "ready" | "error">("idle")
  const [similarItems, setSimilarItems] = useState<CommunityPaperSimilarItem[]>([])
  const [expandedSimilarKey, setExpandedSimilarKey] = useState<string>("")
  const [mobileReaderCollapsed, setMobileReaderCollapsed] = useState(false)
  const analysisPanelRef = useRef<HTMLElement | null>(null)

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

  useEffect(() => {
    if (activeTab !== "similar" || similarState !== "loading") {
      return
    }

    let cancelled = false
    void getCommunityPaperSimilar(paper.id)
      .then((response) => {
        if (cancelled) {
          return
        }
        setSimilarItems(response.items ?? [])
        setExpandedSimilarKey("")
        setSimilarState("ready")
      })
      .catch(() => {
        if (cancelled) {
          return
        }
        setSimilarItems([])
        setSimilarState("error")
      })

    return () => {
      cancelled = true
    }
  }, [activeTab, paper.id, similarState])

  useEffect(() => {
    if (isDesktop || autoFocusedPaperIdRef.current === paper.id) {
      return
    }

    autoFocusedPaperIdRef.current = paper.id
    const scrollTarget = readerPanelRef.current
    if (!scrollTarget) {
      return
    }

    const timer = window.setTimeout(() => {
      scrollTarget.scrollIntoView({
        behavior: "smooth",
        block: "start",
      })
    }, 260)

    return () => {
      window.clearTimeout(timer)
    }
  }, [isDesktop, paper.id])

  useEffect(() => {
    if (isDesktop) {
      setMobileReaderCollapsed(false)
    }
  }, [isDesktop])

  useEffect(() => {
    if (isDesktop || mobileAnalysisJumpRequest === 0) {
      return
    }

    setMobileReaderCollapsed(true)
    const analysisPanel = analysisPanelRef.current
    if (analysisPanel) {
      analysisPanel.scrollIntoView({
        behavior: "smooth",
        block: "start",
      })
    }
  }, [isDesktop, mobileAnalysisJumpRequest])

  const sourceHtmlContent =
    preferredMode === "source" && reader?.source?.kind === "source_html"
      ? (reader.source.html_content ?? null)
      : null
  const sourceDocumentUrl = resolvePdfDocumentUrl(
    `${API_BASE_URL}/api/papers/${paper.id}/source-pdf`,
    reader?.source,
    "source_pdf",
  )
  const translatedPdfUrl = resolvePdfDocumentUrl(
    `${API_BASE_URL}/api/papers/${paper.id}/translated-pdf`,
    reader?.translated,
    "translated_pdf",
  )
  const sourcePdfViewerUrl = buildPdfViewerUrl(sourceDocumentUrl)
  const translatedPdfViewerUrl = buildPdfViewerUrl(translatedPdfUrl)
  const bilingualSourcePdfViewerUrl = buildPdfViewerUrl(sourceDocumentUrl, "bilingual")
  const bilingualTranslatedPdfViewerUrl = buildPdfViewerUrl(translatedPdfUrl, "bilingual")
  const sanitizedSourceHtml = useMemo(
    () =>
      sourceHtmlContent
        ? DOMPurify.sanitize(stripLeadingDuplicatePaperHeaderHtml(sourceHtmlContent, paper) ?? "")
        : null,
    [paper, sourceHtmlContent],
  )
  const selectedInsights = useMemo<StructuredInsightSection[]>(() => {
    const guideSections = structuredInsights?.sections ?? []
    const sectionMap = new Map<StructuredInsightSectionKey, StructuredInsightSection>()
    for (const section of guideSections) {
      if (isGuideSectionKey(section.section_key) && !sectionMap.has(section.section_key)) {
        sectionMap.set(section.section_key, section)
      }
    }

    return GUIDE_SECTION_ORDER.flatMap((sectionKey) => {
      const section = sectionMap.get(sectionKey)
      return section ? [section] : []
    })
  }, [structuredInsights?.sections])
  const hasGuideSections = selectedInsights.length > 0
  const desktopGridColumns = `${splitRatio}fr 12px ${Math.max(1 - splitRatio, 0.18)}fr`

  function handleSelectTab(nextTab: "insights" | "similar") {
    setActiveTab(nextTab)

    if (nextTab === "similar") {
      setSimilarState((currentState) => (currentState === "idle" ? "loading" : currentState))
    }
  }

  function handleExpandReaderFromAnalysis() {
    setMobileReaderCollapsed(false)
    const readerPanel = readerPanelRef.current
    if (readerPanel) {
      readerPanel.scrollIntoView({
        behavior: "smooth",
        block: "start",
      })
    }
  }

  return (
    <div
      ref={containerRef}
      data-testid="paper-detail-top-panels"
      className={cn(
        "flex-1 min-h-0 min-w-0 w-full h-full relative",
        isDesktop ? "grid" : "flex flex-col overflow-y-auto scroll-smooth",
      )}
      style={isDesktop ? { gridTemplateColumns: desktopGridColumns } : undefined}
    >
      <section
        ref={readerPanelRef}
        data-testid="paper-detail-reader-panel"
        data-mobile-reader-viewport={isDesktop ? "default" : mobileReaderCollapsed ? "collapsed" : "immersive"}
        className={cn(
          "flex h-full min-h-0 min-w-0 flex-col overflow-hidden bg-[color:var(--px-shell-panel-strong)]",
          isDesktop
            ? ""
            : mobileReaderCollapsed
              ? "h-[38vh] min-h-[18rem] shrink-0 border-b border-[color:var(--px-shell-line)] bg-white"
              : "min-h-full shrink-0 border-b border-[color:var(--px-shell-line)] bg-white",
        )}
      >
        <div
          data-testid="paper-reader-scroll-root"
          className={cn(
            "relative flex-1 overflow-auto bg-[color:var(--px-shell-panel-strong)]",
            isDesktop ? "" : "overflow-hidden bg-white",
          )}
        >
          {preferredMode === "source" ? (
            sourceDocumentUrl ? (
              <iframe
                data-testid="paper-source-pdf-reader"
                title={`${paper.title} PDF`}
                src={sourcePdfViewerUrl}
                className={cn(
                  "h-full border-0 mx-auto w-[60%] bg-[color:var(--px-shell-panel-strong)]",
                  !isDesktop && "mx-0 w-full bg-white",
                )}
              />
            ) : sanitizedSourceHtml ? (
              <article
                data-testid="paper-source-reader"
                className={cn(
                  "h-full bg-[color:var(--px-shell-panel-strong)] px-6 py-6 text-[color:var(--px-shell-ink)] sm:px-8 lg:px-10 lg:py-8 [&_article]:mx-auto [&_article]:max-w-[1040px] [&_article]:space-y-6 [&_figcaption]:text-sm [&_figcaption]:leading-6 [&_figcaption]:text-[color:var(--px-shell-muted)] [&_figure]:my-8 [&_figure]:overflow-x-auto [&_h1]:mt-8 [&_h1]:text-4xl [&_h1]:font-semibold [&_h1]:tracking-[-0.04em] [&_h2]:mt-10 [&_h2]:text-[1.85rem] [&_h2]:font-semibold [&_h2]:tracking-[-0.03em] [&_h3]:mt-8 [&_h3]:text-[1.35rem] [&_h3]:font-semibold [&_li]:leading-8 [&_ol]:space-y-3 [&_p]:text-[17px] [&_p]:leading-8",
                  !isDesktop &&
                    "bg-white px-4 py-5 [&_article]:max-w-none [&_h1]:mt-4 [&_h1]:text-2xl [&_h2]:mt-7 [&_h2]:text-xl [&_h3]:mt-6 [&_h3]:text-lg [&_p]:text-[15px] [&_p]:leading-7",
                )}
                dangerouslySetInnerHTML={{ __html: sanitizedSourceHtml }}
              />
            ) : (
              <article
                data-testid="paper-source-reader"
                className={cn("flex h-full flex-col gap-4 px-10 py-8", !isDesktop && "bg-white px-4 py-5")}
              >
                {originalSourceUrl ? (
                  <a
                    href={originalSourceUrl}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="inline-flex items-center gap-2 text-sm text-[color:var(--px-shell-accent)] underline-offset-4 hover:underline"
                  >
                    {t("community.detail.originalSource")}
                  </a>
                ) : null}
              </article>
            )
          ) : isTranslatedPdfMode(preferredMode) && canDownload ? (
            <iframe
              data-testid="paper-translated-pdf-reader"
              title={`${paper.title} Translated PDF`}
              src={translatedPdfViewerUrl}
              className={cn(
                "h-full border-0 mx-auto w-[60%] bg-[color:var(--px-shell-panel-strong)]",
                !isDesktop && "mx-0 w-full bg-white",
              )}
            />
          ) : isBilingualCompareMode(preferredMode) && canDownload ? (
            <div
              className={cn(
                "grid h-full min-h-0 grid-cols-2 gap-1 bg-[color:var(--px-shell-panel-strong)] p-1",
                !isDesktop && "gap-0 bg-white p-0",
              )}
            >
              <iframe
                data-testid="paper-bilingual-source-pdf-reader"
                title={`${paper.title} Source PDF`}
                src={bilingualSourcePdfViewerUrl}
                className={cn("h-full w-full border-0 bg-[color:var(--px-shell-panel-strong)]", !isDesktop && "bg-white")}
              />
              <iframe
                data-testid="paper-bilingual-translated-pdf-reader"
                title={`${paper.title} Translated PDF Compare`}
                src={bilingualTranslatedPdfViewerUrl}
                className={cn("h-full w-full border-0 bg-[color:var(--px-shell-panel-strong)]", !isDesktop && "bg-white")}
              />
            </div>
          ) : (
            <article className={cn("flex h-full flex-col gap-4 px-10 py-8", !isDesktop && "bg-white px-4 py-5")}>
              <p className="max-w-4xl text-base leading-8 text-[color:var(--px-shell-muted)]">{abstractText}</p>
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
          <div className="flex h-full w-full items-center justify-center transition-colors group-hover:bg-[color:var(--px-shell-accent-soft)]">
            <div className="h-16 w-1 rounded-full bg-[color:var(--px-shell-line)] group-hover:bg-[color:var(--px-shell-accent)] transition-colors" />
          </div>
        </div>
      ) : null}

      <aside
        ref={analysisPanelRef}
        data-testid="paper-detail-agent-panel"
        className={cn(
          "relative flex min-h-0 min-w-0 shrink-0 flex-col overflow-hidden bg-[color:var(--px-shell-panel-strong)]",
          isDesktop ? "h-full px-3 py-3 pl-0" : "min-h-[75vh] p-3",
        )}
      >
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-none border border-[color:color-mix(in_srgb,var(--px-shell-line)_82%,white)] bg-[color:var(--px-shell-panel)] shadow-[0_24px_60px_-42px_rgba(15,23,42,0.28)]">
          <div data-testid="paper-detail-insights-panel" className="contents" />
          {!isDesktop ? (
            <div className="sticky top-0 z-10 flex items-center justify-center bg-[color:var(--px-shell-panel)] px-3 pb-2 pt-3">
              <Button
                type="button"
                size="sm"
                data-testid="mobile-analysis-collapse-button"
                onClick={handleExpandReaderFromAnalysis}
                className="h-11 min-h-0 w-full rounded-full bg-[color:var(--px-shell-accent)] px-5 text-sm font-extrabold tracking-[0.08em] text-white shadow-[0_18px_32px_-18px_rgba(15,118,210,0.82)] hover:bg-[color:var(--px-shell-accent-strong)]"
              >
                <ChevronUp className="mr-1.5 h-4 w-4" />
                <span>{t("community.detail.mobile.backToReader", { defaultValue: "Back to reader" })}</span>
              </Button>
            </div>
          ) : null}
          <EditorialTabs
            value={activeTab}
            onValueChange={(nextValue) => handleSelectTab(nextValue as "insights" | "similar")}
            className="flex min-h-0 flex-1 flex-col"
          >
            <EditorialTabsList className="mx-4 mt-4 shrink-0 rounded-none bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_88%,white)]">
              <EditorialTabsTrigger value="insights" className="rounded-none">
                {t("community.detail.tab.insights")}
              </EditorialTabsTrigger>
              <EditorialTabsTrigger value="similar" className="rounded-none">
                {t("community.detail.tab.similar")}
              </EditorialTabsTrigger>
            </EditorialTabsList>

            {activeTab === "insights" ? (
              <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-4 pt-5 space-y-3">
                {actionError ? (
                  <NoticeBanner tone="danger" description={actionError} className="rounded-none" />
                ) : null}

                {structuredInsights?.state === "processing" || structuredInsights?.state === "queued" ? (
                  <StatePanel
                    className="rounded-none px-4 py-8 shadow-none"
                    title={t("community.detail.insightsPendingTitle")}
                    description={t("community.detail.insightsPendingDescription")}
                  />
                ) : hasGuideSections ? (
                  selectedInsights.map((section) => {
                    const expanded = expandedInsightKey === section.section_key
                    const parsedContent = resolveInsightContent(section)

                    return (
                      <DisclosureCard
                        key={section.section_key}
                        open={expanded}
                        onOpenChange={(nextOpen) => setExpandedInsightKey(nextOpen ? section.section_key : "")}
                        title={getInsightLabel(section.section_key, t)}
                      >
                        {parsedContent ? (
                          <div className="space-y-3">
                            {parsedContent.summary ? (
                              <p className="font-medium leading-7 text-[color:var(--px-shell-ink)] whitespace-pre-wrap">
                                {parsedContent.summary}
                              </p>
                            ) : null}
                            {parsedContent.sections.map((item) => (
                              <div
                                key={`${section.section_key}-${item.title}`}
                                className="space-y-1.5 border-l-2 border-[color:var(--px-shell-line)] pl-3"
                              >
                                <p className="text-[12px] font-semibold tracking-[0.06em] text-[color:var(--px-shell-ink)]/85">
                                  {item.title}
                                </p>
                                <p className="whitespace-pre-wrap leading-7 text-[color:var(--px-shell-ink)]">{item.body}</p>
                              </div>
                            ))}
                            {parsedContent.paragraphs.map((paragraph, index) => (
                              <p
                                key={`${section.section_key}-paragraph-${index}`}
                                className="whitespace-pre-wrap leading-7 text-[color:var(--px-shell-ink)]"
                              >
                                {paragraph}
                              </p>
                            ))}
                          </div>
                        ) : (
                          <p>{t("community.detail.insights.languagePending")}</p>
                        )}
                      </DisclosureCard>
                    )
                  })
                ) : (
                  <StatePanel
                    className="rounded-none px-4 py-8 shadow-none"
                    borderStyle="dashed"
                    title={t("community.detail.insightsEmptyTitle")}
                    description={t("community.detail.insightsEmptyDescription")}
                  />
                )}
              </div>
            ) : (
              <div className="flex-1 min-h-0 overflow-y-auto px-4 pb-4 pt-5">
                {similarState === "loading" ? (
                  <NoticeBanner title={t("community.detail.similar.loading")} />
                ) : null}

                {similarState === "error" ? (
                  <StatePanel
                    className="rounded-none px-4 py-8 shadow-none"
                    tone="danger"
                    title={t("community.detail.similar.errorTitle")}
                    description={t("community.detail.similar.errorDescription")}
                  />
                ) : null}

                {similarState === "ready" && similarItems.length === 0 ? (
                  <StatePanel
                    className="rounded-none px-4 py-8 shadow-none"
                    borderStyle="dashed"
                    title={t("community.detail.similar.emptyTitle")}
                    description={t("community.detail.similar.emptyDescription")}
                  />
                ) : null}

                {similarState === "ready" && similarItems.length > 0 ? (
                  <div className="space-y-3">
                    {similarItems.map((item) => {
                      const itemKey = `${item.arxiv_id}-${item.community_paper_id ?? item.arxiv_url}`
                      const expanded = expandedSimilarKey === itemKey
                      const destination = item.community_paper_id ? (
                        <Link
                          to={`/paper/${item.community_paper_id}`}
                          className="inline-flex text-sm font-medium text-[color:var(--px-shell-accent)] underline-offset-4 hover:underline"
                        >
                          {t("community.detail.similar.openInCommunity")}
                        </Link>
                      ) : (
                        <a
                          href={item.arxiv_url}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="inline-flex text-sm font-medium text-[color:var(--px-shell-accent)] underline-offset-4 hover:underline"
                        >
                          {t("community.detail.similar.openInArxiv")}
                        </a>
                      )

                      return (
                        <DisclosureCard
                          key={itemKey}
                          open={expanded}
                          onOpenChange={(nextOpen) => setExpandedSimilarKey(nextOpen ? itemKey : "")}
                          eyebrow={item.arxiv_id}
                          title={item.title}
                          headerAside={destination}
                        >
                          <p className="text-xs leading-6 text-[color:var(--px-shell-muted)]">{item.abstract}</p>
                        </DisclosureCard>
                      )
                    })}
                  </div>
                ) : null}
              </div>
            )}
          </EditorialTabs>
        </div>
      </aside>
    </div>
  )
}
