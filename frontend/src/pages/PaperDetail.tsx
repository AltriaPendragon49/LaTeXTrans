import { ArrowLeft, ChevronDown, ChevronUp, Download, Languages, Timer } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { Link, useNavigate, useParams } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import { PaperDetailSkeleton } from "@/components/community/PaperDetailSkeleton"
import { PaperDetailWorkspace } from "@/components/community/PaperDetailWorkspace"
import { usePaperDetail } from "@/hooks/use-paper-detail"
import {
  createCommunityPaperDownloadSession,
  translateCommunityPaper,
} from "@/lib/community-api"
import { useStore } from "@/store/useStore"
import type { CommunityPaperReaderMode } from "@/types/community"

function formatAuthors(authors: unknown[], fallback: string) {
  if (!authors.length) {
    return fallback
  }

  return authors
    .map((entry) => {
      if (typeof entry === "string") {
        return entry
      }
      if (entry && typeof entry === "object" && "name" in entry) {
        const name = (entry as { name?: unknown }).name
        return typeof name === "string" ? name : null
      }
      return null
    })
    .filter(Boolean)
    .join(", ")
}

function extractActionErrorMessage(error: unknown): string | null {
  if (typeof error === "string") {
    return error
  }
  if (error instanceof Error) {
    return error.message
  }
  if (!error || typeof error !== "object") {
    return null
  }
  if ("response" in error) {
    const response = error.response
    if (
      response &&
      typeof response === "object" &&
      "data" in response &&
      response.data &&
      typeof response.data === "object" &&
      "detail" in response.data &&
      typeof response.data.detail === "string"
    ) {
      return response.data.detail
    }
  }
  if ("message" in error && typeof error.message === "string") {
    return error.message
  }
  return null
}

function resolveStageLabel(
  transStatus: string | undefined,
  readerState: "ready" | "warming" | "unavailable",
  hasTranslatedMode: boolean,
  t: (key: string) => string,
) {
  if (hasTranslatedMode && readerState === "ready") {
    return t("community.detail.stage.translatedReady")
  }
  if (transStatus === "queued" || transStatus === "processing" || readerState === "warming") {
    return t("community.detail.stage.generating")
  }
  if (readerState === "ready") {
    return t("community.detail.stage.sourceReady")
  }
  return t("community.detail.stage.unavailable")
}

function hasTranslatedHtmlResource(
  paper: {
    latest_asset?: { asset_type?: string | null } | null
  } | null | undefined,
  preview: { html_content?: string | null } | null | undefined,
  reader: {
    translated?: { kind?: string | null; html_content?: string | null } | null
  } | null | undefined,
) {
  return Boolean(
    preview?.html_content ||
      reader?.translated?.html_content ||
      reader?.translated?.kind === "preview_html" ||
      paper?.latest_asset?.asset_type === "preview_html",
  )
}

function hasTranslatedPdfResource(
  paper: {
    assets?: { translated_pdf?: unknown } | null
    latest_asset?: { asset_type?: string | null } | null
    trans_status?: string | null
  } | null | undefined,
  reader: {
    translated?: { kind?: string | null } | null
  } | null | undefined,
) {
  return Boolean(
    paper?.assets?.translated_pdf ||
      reader?.translated?.kind === "translated_pdf" ||
      paper?.latest_asset?.asset_type === "translated_pdf" ||
      paper?.trans_status === "completed",
  )
}

function hasSourcePdfResource(
  paper: {
    arxiv_id?: string | null
  } | null | undefined,
  reader: {
    source?: { kind?: string | null } | null
  } | null | undefined,
) {
  return Boolean(reader?.source?.kind === "source_pdf" || paper?.arxiv_id)
}

function resolveAvailableModes(
  paper: {
    arxiv_id?: string | null
    trans_status?: string | null
    assets?: { translated_pdf?: unknown } | null
    latest_asset?: { asset_type?: string | null } | null
  } | null | undefined,
  preview: { html_content?: string | null } | null | undefined,
  reader: {
    available_modes?: CommunityPaperReaderMode[] | null
    source?: { kind?: string | null } | null
    translated?: { kind?: string | null; html_content?: string | null } | null
  } | null | undefined,
): CommunityPaperReaderMode[] {
  const modes: CommunityPaperReaderMode[] = ["source"]
  const rawModes = reader?.available_modes ?? []
  const allowTranslatedHtml =
    rawModes.includes("translated_html") ||
    rawModes.includes("translated") ||
    hasTranslatedHtmlResource(paper, preview, reader)
  const allowTranslatedPdf =
    rawModes.includes("translated_pdf") ||
    (rawModes.includes("translated") && hasTranslatedPdfResource(paper, reader)) ||
    hasTranslatedPdfResource(paper, reader)

  if (allowTranslatedHtml) {
    modes.push("translated_html")
  }
  if (allowTranslatedPdf) {
    modes.push("translated_pdf")
  }
  if (allowTranslatedPdf && hasSourcePdfResource(paper, reader)) {
    modes.push("bilingual_compare")
  }

  return modes
}

function resolvePreferredMode(
  preferredMode: CommunityPaperReaderMode | undefined,
  availableModes: CommunityPaperReaderMode[],
): CommunityPaperReaderMode {
  if (preferredMode === "translated" && availableModes.includes("translated_pdf")) {
    return "translated_pdf"
  }
  if (availableModes.includes("translated_pdf")) {
    return "translated_pdf"
  }
  if (preferredMode && availableModes.includes(preferredMode)) {
    return preferredMode
  }
  if (availableModes.includes("translated_html")) {
    return "translated_html"
  }
  return "source"
}

export default function PaperDetailPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { paperId } = useParams<{ paperId: string }>()
  const {
    paper,
    preview,
    readerState,
    reader,
    structuredInsights,
    loading,
    error,
    notFound,
  } = usePaperDetail(paperId)
  const { config, setTaskId, setArxivId } = useStore()
  const [isHeaderExpanded, setIsHeaderExpanded] = useState(true)
  const [selectedMode, setSelectedMode] = useState<CommunityPaperReaderMode>("source")
  const [actionError, setActionError] = useState<string | null>(null)

  const availableModes = useMemo<CommunityPaperReaderMode[]>(
    () => resolveAvailableModes(paper, preview, reader),
    [paper, preview, reader],
  )

  useEffect(() => {
    setSelectedMode(resolvePreferredMode(reader?.preferred_mode, availableModes))
  }, [availableModes, reader?.preferred_mode])

  if (loading) {
    return <PaperDetailSkeleton />
  }

  if (error && !notFound) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 py-16">
        <div className="max-w-lg space-y-3 text-center">
          <h1 className="text-3xl font-semibold text-on-surface">{t("community.detail.errorTitle")}</h1>
          <p className="text-sm leading-7 text-on-surface-variant">{t("community.detail.errorDescription")}</p>
          <p className="text-sm text-destructive">{error}</p>
        </div>
      </div>
    )
  }

  if (notFound || !paper) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 py-16">
        <div className="max-w-lg space-y-3 text-center">
          <h1 className="text-3xl font-semibold text-on-surface">{t("community.detail.notFoundTitle")}</h1>
          <p className="text-sm leading-7 text-on-surface-variant">{t("community.detail.notFoundDescription")}</p>
        </div>
      </div>
    )
  }

  const activePaper = paper
  const authorsLabel = formatAuthors(activePaper.authors, t("community.card.authorsUnavailable"))
  const hasTranslatedMode =
    availableModes.includes("translated_html") || availableModes.includes("translated_pdf")
  const stageLabel = resolveStageLabel(activePaper.trans_status, readerState, hasTranslatedMode, t)
  const canTranslate = activePaper.trans_status === "not_started" || activePaper.trans_status === "failed"
  const canViewProgress =
    Boolean(activePaper.community_selected_task_id) &&
    (activePaper.trans_status === "queued" || activePaper.trans_status === "processing")
  const canDownload = activePaper.trans_status === "completed"
  const originalSourceUrl =
    reader?.source?.url ??
    (activePaper.arxiv_id ? `https://arxiv.org/abs/${activePaper.arxiv_id}` : null)
  const abstractText =
    (selectedMode === "source" ? activePaper.abstract_raw : activePaper.abstract_translated) ||
    activePaper.abstract_raw ||
    activePaper.abstract_translated ||
    t("community.detail.abstractUnavailable")

  async function handleTranslate() {
    if (!paperId) {
      return
    }

    try {
      setActionError(null)
      const response = await translateCommunityPaper(paperId, config)
      setTaskId(response.task_id)
      setArxivId(activePaper.arxiv_id)
      navigate(response.processing_url)
    } catch (translateError) {
      setActionError(extractActionErrorMessage(translateError) ?? t("community.actions.translateError"))
    }
  }

  function handleViewProgress() {
    if (!activePaper.community_selected_task_id) {
      return
    }
    setTaskId(activePaper.community_selected_task_id)
    setArxivId(activePaper.arxiv_id)
    navigate(`/processing?taskId=${activePaper.community_selected_task_id}`)
  }

  async function handleDownload() {
    if (!paperId) {
      return
    }

    try {
      setActionError(null)
      const session = await createCommunityPaperDownloadSession(paperId)
      const downloadUrl = session.download_url.startsWith("http")
        ? session.download_url
        : `${API_BASE_URL}${session.download_url}`
      window.open(downloadUrl, "_blank")
    } catch (downloadError) {
      setActionError(extractActionErrorMessage(downloadError) ?? t("community.actions.downloadError"))
    }
  }

  return (
    <div
      data-testid="paper-detail-page-shell"
      className="flex-1 flex min-h-0 flex-col min-w-0 bg-surface-container-lowest h-full overflow-hidden"
    >
      <nav className="shrink-0 flex flex-col border-b border-outline-variant/30 bg-surface-container-lowest z-10 sticky top-0 transition-all duration-300">
        <div className="h-12 flex items-center justify-between px-6 border-b border-outline-variant/10 relative">
          <div className="flex items-center gap-4 min-w-0 flex-1">
            <Link
              to="/"
              className="p-2 text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest rounded-full transition-colors shrink-0 outline-none focus-visible:ring-2 focus-visible:ring-primary"
              aria-label={t("community.detail.backToFeed")}
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <h1 className="text-lg font-bold text-on-surface truncate" title={activePaper.title}>
              {activePaper.title}
            </h1>
          </div>

          <div className="flex items-center gap-3 shrink-0 ml-4">
            <div className="text-xs font-black uppercase tracking-[0.2em] text-primary/40 mr-4 hidden md:block">
              Lumina Archive
            </div>

            <div className="flex bg-surface-container-low rounded-xl p-1 border border-outline-variant/30 shadow-sm overflow-hidden">
              <button
                type="button"
                data-testid="paper-detail-mode-source"
                onClick={() => setSelectedMode("source")}
                className={`px-4 py-1.5 text-xs font-bold tracking-wider rounded-lg transition-all ${
                  selectedMode === "source"
                    ? "bg-surface-container-highest text-on-surface shadow-sm border border-outline-variant/30"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50 border border-transparent"
                }`}
              >
                {t("community.detail.mode.source")}
              </button>
              <button
                type="button"
                data-testid="paper-detail-mode-translated-pdf"
                disabled={!availableModes.includes("translated_pdf")}
                onClick={() => setSelectedMode("translated_pdf")}
                className={`px-4 py-1.5 text-xs font-bold tracking-wider rounded-lg transition-all ${
                  selectedMode === "translated_pdf"
                    ? "bg-surface-container-highest text-on-surface shadow-sm border border-outline-variant/30"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50 border border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                }`}
              >
                {t("community.detail.mode.translatedPdf")}
              </button>
              <button
                type="button"
                data-testid="paper-detail-mode-translated-html"
                disabled={!availableModes.includes("translated_html")}
                onClick={() => setSelectedMode("translated_html")}
                className={`px-4 py-1.5 text-xs font-bold tracking-wider rounded-lg transition-all ${
                  selectedMode === "translated_html"
                    ? "bg-surface-container-highest text-on-surface shadow-sm border border-outline-variant/30"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50 border border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                }`}
              >
                {t("community.detail.mode.translatedHtml")}
              </button>
              <button
                type="button"
                data-testid="paper-detail-mode-bilingual-compare"
                disabled={!availableModes.includes("bilingual_compare")}
                onClick={() => setSelectedMode("bilingual_compare")}
                className={`px-4 py-1.5 text-xs font-bold tracking-wider rounded-lg transition-all ${
                  selectedMode === "bilingual_compare"
                    ? "bg-surface-container-highest text-on-surface shadow-sm border border-outline-variant/30"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-highest/50 border border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
                }`}
              >
                {t("community.detail.mode.bilingualCompare")}
              </button>
            </div>

            <div className="w-px h-6 bg-outline-variant/30 mx-1 hidden sm:block" />

            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-primary/10 border border-primary/20 flex items-center justify-center text-[10px] font-bold text-primary">
                UA
              </div>
              {!isHeaderExpanded ? (
                <button
                  onClick={() => setIsHeaderExpanded(true)}
                  className="p-1 text-on-surface-variant hover:text-primary transition-colors ml-1"
                  title="Expand Header"
                >
                  <ChevronDown className="w-4 h-4" />
                </button>
              ) : null}
            </div>
          </div>
        </div>

        {isHeaderExpanded ? (
          <div className="animate-in slide-in-from-top-1 duration-200">
            <div className="h-8 flex items-center justify-between px-6 border-b border-outline-variant/10 bg-surface-container-lowest/50">
              <div className="flex items-center gap-6 text-[10px] font-bold text-on-surface-variant/70 uppercase tracking-widest overflow-hidden">
                <div className="flex items-center gap-2 max-w-2xl truncate">
                  <span className="text-on-surface-variant font-black">Authors:</span>
                  <span className="truncate">{authorsLabel}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-on-surface-variant font-black">Published:</span>
                  <span>{activePaper.official_published_at ? new Date(activePaper.official_published_at).toLocaleDateString() : (activePaper.created_at ? new Date(activePaper.created_at).toLocaleDateString() : "N/A")}</span>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className="bg-primary/10 text-primary px-2 py-0.5 rounded text-[8px] font-black tracking-tighter">PEER REVIEWED</span>
                </div>
              </div>

              <div className="flex items-center gap-4 shrink-0">
                {canTranslate && !canViewProgress ? (
                  <button
                    type="button"
                    onClick={() => void handleTranslate()}
                    className="text-[9px] font-black uppercase tracking-widest text-primary hover:text-primary-dim transition-colors flex items-center gap-1.5"
                  >
                    <Languages className="w-3 h-3" />
                    {t("community.actions.translate")}
                  </button>
                ) : null}
                {canViewProgress ? (
                  <button
                    type="button"
                    onClick={handleViewProgress}
                    className="text-[9px] font-black uppercase tracking-widest text-primary hover:text-primary-dim transition-colors flex items-center gap-1.5"
                  >
                    <Timer className="w-3 h-3" />
                    {t("community.actions.viewProgress")}
                  </button>
                ) : null}
                <button
                  type="button"
                  disabled={!canDownload}
                  onClick={() => void handleDownload()}
                  className="text-[9px] font-black uppercase tracking-widest text-on-surface-variant hover:text-on-surface transition-colors flex items-center gap-1.5 disabled:opacity-30"
                >
                  <Download className="w-3 h-3" />
                  {t("community.actions.download")}
                </button>
              </div>
            </div>

            <div className="h-8 flex items-center px-6 gap-8 bg-surface-container-lowest relative">
              <div className="flex items-center gap-2">
                <div className="text-[9px] font-black text-on-surface-variant/40 uppercase tracking-tighter">Likes</div>
                <div className="text-[10px] font-bold text-on-surface">{activePaper.like_count || 0}</div>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-[9px] font-black text-on-surface-variant/40 uppercase tracking-tighter">Saves</div>
                <div className="text-[10px] font-bold text-on-surface">{activePaper.favorite_count || 0}</div>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-[9px] font-black text-on-surface-variant/40 uppercase tracking-tighter">Visibility</div>
                <div className="text-[10px] font-bold text-on-surface">Public</div>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-[9px] font-black text-on-surface-variant/40 uppercase tracking-tighter">Views</div>
                <div className="text-[10px] font-bold text-on-surface">{activePaper.view_count || 0}</div>
              </div>

              <div className="ml-auto flex items-center gap-3">
                <div className="px-2 py-0.5 rounded text-[8px] font-black tracking-tighter uppercase bg-primary/10 text-primary">
                  {actionError ? "Error" : stageLabel}
                </div>
                <button
                  onClick={() => setIsHeaderExpanded(false)}
                  className="p-1 text-on-surface-variant hover:text-primary transition-colors"
                  title="Collapse Header"
                >
                  <ChevronUp className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </nav>

      <div className="flex-1 flex min-h-0 min-w-0 overflow-hidden relative">
        <PaperDetailWorkspace
          paper={activePaper}
          preview={preview}
          readerState={readerState}
          reader={reader}
          preferredMode={selectedMode}
          structuredInsights={structuredInsights}
          originalSourceUrl={originalSourceUrl}
          abstractText={abstractText}
          canDownload={canDownload}
          actionError={actionError}
        />
      </div>
    </div>
  )
}
