import { ArrowLeft, Clock3, Link2 } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Link, useNavigate, useParams } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import { PaperDetailSkeleton } from "@/components/community/PaperDetailSkeleton"
import { PaperDetailWorkspace } from "@/components/community/PaperDetailWorkspace"
import { Button } from "@/components/ui/button"
import { usePaperDetail } from "@/hooks/use-paper-detail"
import {
  createCommunityAgentRun,
  createCommunityPaperDownloadSession,
  importCommunityPaper,
  translateCommunityPaper,
} from "@/lib/community-api"
import { useStore } from "@/store/useStore"
import type {
  CommunityAgentCitation,
  CommunityAgentRun,
  CommunityPaper,
  CommunityPaperExperience,
  CommunityPaperReader,
  CommunityPaperReaderMode,
  PaperAssetSummary,
} from "@/types/community"

function getAssetTypeLabel(assetType: PaperAssetSummary["asset_type"], t: (key: string) => string) {
  switch (assetType) {
    case "source_archive":
      return t("community.card.assetType.source_archive")
    case "translated_pdf":
      return t("community.card.assetType.translated_pdf")
    case "preview_pdf":
      return t("community.card.assetType.preview_pdf")
    case "preview_html":
      return t("community.card.assetType.preview_html")
    default:
      return assetType
  }
}

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

function formatDetailDate(value: string | null | undefined, locale: string, fallback: string) {
  if (!value) {
    return fallback
  }

  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return fallback
  }

  return new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(parsed)
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

const ACTIVE_TRANSLATION_STATUSES = new Set<CommunityPaper["trans_status"]>(["queued", "processing"])
const FAILED_TRANSLATION_STATUSES = new Set<CommunityPaper["trans_status"]>(["failed"])

function hasSourceReader(reader: CommunityPaperReader | null | undefined) {
  return reader?.state === "source_ready" || Boolean(reader?.source)
}

function hasTranslatedReaderResource(reader: CommunityPaperReader | null | undefined) {
  return reader?.state === "translated_ready" || Boolean(reader?.translated)
}

function resolveStageKey(
  paper: Pick<CommunityPaper, "trans_status"> | null | undefined,
  reader: CommunityPaperReader | null | undefined,
  experience: CommunityPaperExperience | null | undefined,
) {
  if (hasTranslatedReaderResource(reader)) {
    return "community.detail.stage.translatedReady"
  }

  if (reader?.state === "warming" || ACTIVE_TRANSLATION_STATUSES.has(paper?.trans_status ?? "not_started")) {
    return "community.detail.stage.generating"
  }

  if (
    hasSourceReader(reader) &&
    (experience?.failure_type === "translation_failed" ||
      FAILED_TRANSLATION_STATUSES.has(paper?.trans_status ?? "not_started"))
  ) {
    return "community.detail.stage.sourceFallback"
  }

  if (hasSourceReader(reader)) {
    return "community.detail.stage.sourceReady"
  }

  return "community.detail.stage.unavailable"
}

export default function PaperDetailPage() {
  const { i18n, t } = useTranslation()
  const navigate = useNavigate()
  const previewRef = useRef<HTMLDivElement>(null)
  const { paperId } = useParams<{ paperId: string }>()
  const { paper, preview, readerState, reader, experience, loading, error, notFound, refetch } =
    usePaperDetail(paperId)
  const { config, loadUserSettings, setTaskId, setArxivId } = useStore()
  const [actionError, setActionError] = useState<string | null>(null)
  const [statusOverride, setStatusOverride] = useState<string | null>(null)
  const [canLeaveHint, setCanLeaveHint] = useState<string | null>(null)
  const [softBanner, setSoftBanner] = useState<string | null>(null)
  const [readerHighlight, setReaderHighlight] = useState(false)
  const [agentBusy, setAgentBusy] = useState(false)
  const [agentError, setAgentError] = useState<string | null>(null)
  const [agentRun, setAgentRun] = useState<CommunityAgentRun | null>(null)
  const [selectedMode, setSelectedMode] = useState<CommunityPaperReaderMode>("source")
  const hasTranslatedReader = Boolean(reader?.translated)
  const resolvedStageKey = resolveStageKey(paper, reader, experience)
  const resolvedPreferredMode: CommunityPaperReaderMode =
    reader?.preferred_mode ??
    (preview ||
    paper?.trans_status === "completed" ||
    paper?.trans_status === "processing" ||
    paper?.trans_status === "queued" ||
    paper?.latest_asset?.asset_type === "preview_html"
      ? "translated"
      : "source")
  const availableModes: CommunityPaperReaderMode[] = reader?.available_modes?.length
    ? reader.available_modes
    : (hasTranslatedReader ? ["source", "translated"] : ["source"])

  useEffect(() => {
    if (resolvedStageKey === "community.detail.stage.translatedReady") {
      setSoftBanner(t("community.detail.softReady"))
      setReaderHighlight(true)
      const timer = window.setTimeout(() => {
        setReaderHighlight(false)
      }, 1500)
      return () => window.clearTimeout(timer)
    }
    return undefined
  }, [resolvedStageKey, t])

  useEffect(() => {
    if (statusOverride === "community.detail.stage.generating") {
      const intervalId = window.setInterval(() => {
        void refetch().catch(() => undefined)
      }, 3000)
      return () => window.clearInterval(intervalId)
    }
    return undefined
  }, [refetch, statusOverride])

  useEffect(() => {
    setSelectedMode((currentMode) => {
      if (availableModes.includes(currentMode)) {
        return currentMode
      }
      return resolvedPreferredMode
    })
  }, [availableModes, resolvedPreferredMode])

  useEffect(() => {
    if (resolvedStageKey === "community.detail.stage.translatedReady") {
      setSelectedMode("translated")
    }
  }, [resolvedStageKey])

  if (loading) {
    return (
      <div className="min-h-full bg-[var(--shell-bg)] px-4 py-6 text-[var(--shell-text)] transition-colors sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-[2520px]">
          <PaperDetailSkeleton />
        </div>
      </div>
    )
  }

  if (error && !notFound && !paper) {
    return (
      <div className="min-h-full bg-[var(--shell-bg)] px-4 py-6 text-[var(--shell-text)] transition-colors sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl rounded-[32px] border border-rose-500/20 bg-rose-500/5 px-6 py-14 text-center">
          <h1 className="text-3xl font-semibold text-rose-950 dark:text-white">
            {t("community.detail.errorTitle")}
          </h1>
          <p className="mt-3 text-sm text-rose-900/80 dark:text-slate-300">
            {t("community.detail.errorDescription")}
          </p>
          <p className="mt-4 text-xs text-rose-800/80 dark:text-slate-400">{error}</p>
          <Button
            asChild
            variant="outline"
            className="mt-6 rounded-2xl border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-heading)]"
          >
            <Link to="/">{t("community.detail.backToFeed")}</Link>
          </Button>
        </div>
      </div>
    )
  }

  if (notFound || !paper) {
    return (
      <div className="min-h-full bg-[var(--shell-bg)] px-4 py-6 text-[var(--shell-text)] transition-colors sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl rounded-[32px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] px-6 py-14 text-center">
          <h1 className="text-3xl font-semibold text-[var(--shell-heading)]">
            {t("community.detail.notFoundTitle")}
          </h1>
          <p className="mt-3 text-sm text-[var(--shell-text-muted)]">
            {t("community.detail.notFoundDescription")}
          </p>
          <Button
            asChild
            variant="outline"
            className="mt-6 rounded-2xl border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-heading)]"
          >
            <Link to="/">{t("community.detail.backToFeed")}</Link>
          </Button>
        </div>
      </div>
    )
  }

  const activePaper = paper
  const includedAtLabel = formatDetailDate(
    activePaper.created_at,
    i18n.language,
    t("community.detail.unavailable"),
  )
  const originalSourceUrl =
    activePaper.source === "arxiv" && activePaper.arxiv_id
      ? `https://arxiv.org/abs/${activePaper.arxiv_id}`
      : null
  const authorsLabel = formatAuthors(activePaper.authors, t("community.card.authorsUnavailable"))
  const abstractText =
    selectedMode === "translated"
      ? activePaper.abstract_translated || activePaper.abstract_raw || t("community.detail.abstractUnavailable")
      : activePaper.abstract_raw || activePaper.abstract_translated || t("community.detail.abstractUnavailable")
  const assetLabel = activePaper.latest_asset
    ? `${getAssetTypeLabel(activePaper.latest_asset.asset_type, t)} · ${activePaper.latest_asset.file_name}`
    : t("community.card.assetUnavailable")
  const canTranslate = !hasTranslatedReader && ["not_started", "failed"].includes(activePaper.trans_status)
  const canViewProgress = Boolean(
    activePaper.community_selected_task_id && ["queued", "processing"].includes(activePaper.trans_status),
  )
  const canDownload = Boolean(
    activePaper.assets?.translated_pdf ||
      reader?.translated?.kind === "translated_pdf" ||
      activePaper.latest_asset?.asset_type === "translated_pdf" ||
      activePaper.trans_status === "completed",
  )
  const stageLabel = t(
    statusOverride ??
      resolvedStageKey ??
      (selectedMode === "source"
        ? "community.detail.stage.sourceReady"
        : "community.detail.stage.translatedReady"),
  )
  const detailMetaItems = [
    {
      key: "includedAt",
      icon: Clock3,
      label: t("community.detail.includedAt", { value: includedAtLabel }),
      ariaLabel: t("community.detail.includedAt", { value: includedAtLabel }),
    },
  ]

  async function handleTranslate() {
    if (!paperId) {
      return
    }

    try {
      setActionError(null)
      await loadUserSettings()
      const response = await translateCommunityPaper(paperId, {
        source_language: config.source_language,
        target_language: config.target_language,
        advanced_config: config.advanced_config,
      })
      setTaskId(response.task_id)
      setArxivId(activePaper.arxiv_id)
      setStatusOverride("community.detail.stage.generating")
      setCanLeaveHint(t("community.detail.canLeave"))
      setSoftBanner(null)
    } catch (translateError) {
      setActionError(extractActionErrorMessage(translateError) ?? t("community.actions.translateError"))
    }
  }

  async function handleAgentQuickRun(input: string) {
    if (!paperId) {
      return
    }

    try {
      setAgentBusy(true)
      setAgentError(null)
      const run = await createCommunityAgentRun({
        input,
        paper_id: paperId,
        context: {
          source: "paper_detail",
          current_mode: selectedMode,
        },
      })
      setAgentRun(run)
    } catch (runError) {
      setAgentError(extractActionErrorMessage(runError) ?? t("community.agent.error"))
    } finally {
      setAgentBusy(false)
    }
  }

  async function handleAgentCitationOpen(citation: CommunityAgentCitation) {
    if (citation.paper_id) {
      navigate(`/paper/${citation.paper_id}`)
      return
    }

    if (citation.arxiv_id) {
      const imported = await importCommunityPaper({
        source: "arxiv",
        arxiv_id: citation.arxiv_id,
      })
      navigate(`/paper/${imported.paper_id}`)
      return
    }

    if (citation.url) {
      window.open(citation.url, "_blank", "noopener,noreferrer")
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

  function handlePreview() {
    if (availableModes.includes("translated")) {
      setSelectedMode("translated")
    }
    window.setTimeout(() => {
      const target =
        previewRef.current ??
        document.getElementById("paper-preview-reader") ??
        document.querySelector<HTMLElement>('[data-testid="paper-detail-reader-panel"]')
      target?.scrollIntoView({ behavior: "smooth", block: "start" })
    }, 0)
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
      const detail = extractActionErrorMessage(downloadError)
      setActionError(
        detail?.includes("Translated PDF")
          ? t("community.actions.downloadUnavailable")
          : (detail ?? t("community.actions.downloadError")),
      )
    }
  }

  return (
    <div
      data-testid="paper-detail-page-shell"
      className="min-h-full bg-[var(--shell-bg)] px-4 py-4 text-[var(--shell-text)] transition-colors sm:px-6 lg:px-8"
    >
      <div className="mx-auto w-full max-w-[2800px] space-y-3">
        <Button
          asChild
          variant="ghost"
          className="min-h-10 rounded-full border border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-4 text-[var(--shell-heading)] hover:bg-[var(--shell-pill-hover)]"
        >
          <Link to="/">
            <ArrowLeft className="h-4 w-4" />
            {t("community.detail.backToFeed")}
          </Link>
        </Button>

        <section className="rounded-[28px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-4 shadow-[var(--shell-panel-shadow-strong)] sm:p-5">
          <div className="space-y-2">
            <h1 className="max-w-5xl text-balance text-[1.95rem] font-semibold tracking-tight text-[var(--shell-heading)] sm:text-[2.65rem]">
              {activePaper.title}
            </h1>
            <p className="max-w-3xl text-[15px] text-[var(--shell-text-soft)]">{authorsLabel}</p>
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--shell-text-muted)]">
                {activePaper.categories.length
                ? activePaper.categories.join(" · ")
                : t("community.card.categoriesUnavailable")}
              </p>
          </div>

          <div
            data-testid="paper-detail-header-metadata"
            className="mt-4 flex flex-wrap items-center gap-2 border-t border-[color:var(--shell-border-strong)] pt-3"
          >
            <div className="rounded-full border border-[color:var(--shell-border-strong)] bg-[var(--shell-pill)] px-3 py-2 text-xs text-[var(--shell-text-muted)]">
              {activePaper.source === "arxiv"
                ? t("community.detail.sourceArxiv")
                : t("community.detail.sourceUpload")}
            </div>
            {activePaper.arxiv_id ? (
              <div className="rounded-full border border-[color:var(--shell-border-strong)] bg-[var(--shell-pill)] px-3 py-2 text-xs text-[var(--shell-text-muted)]">
                {t("community.detail.arxivBadge", { value: activePaper.arxiv_id })}
              </div>
            ) : null}
            {detailMetaItems.map(({ key, icon: Icon, label, ariaLabel }) => (
              <div
                key={key}
                aria-label={ariaLabel}
                className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-[color:var(--shell-border-strong)] bg-[var(--shell-pill)] px-3 py-2 text-xs text-[var(--shell-text-muted)]"
              >
                <Icon className="h-3.5 w-3.5 text-[var(--shell-text-muted)]" />
                <span className="tabular-nums text-[var(--shell-text-soft)]">{label}</span>
              </div>
            ))}
            {originalSourceUrl ? (
              <a
                href={originalSourceUrl}
                target="_blank"
                rel="noreferrer noopener"
                className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-[color:var(--shell-border-strong)] bg-[var(--shell-pill)] px-3 py-2 text-xs text-[var(--shell-text-soft)] transition-colors hover:text-[var(--shell-heading)]"
              >
                <Link2 className="h-3.5 w-3.5 text-[var(--shell-text-muted)]" />
                <span className="font-medium text-[var(--shell-text-muted)]">
                  {t("community.detail.originalSource")}
                </span>
                <span className="break-all text-[var(--shell-text-soft)]">{originalSourceUrl}</span>
              </a>
            ) : null}
          </div>

          <PaperDetailWorkspace
            paper={activePaper}
            preview={preview}
            readerState={readerState}
            reader={reader}
            preferredMode={selectedMode}
            availableModes={availableModes}
            stageLabel={stageLabel}
            softBanner={softBanner}
            canLeaveHint={canLeaveHint ?? experience?.can_leave_hint ?? null}
            originalSourceUrl={originalSourceUrl}
            assetLabel={assetLabel}
            abstractText={abstractText}
            readerHighlight={readerHighlight}
            previewRef={previewRef}
            canTranslate={canTranslate}
            canViewProgress={canViewProgress}
            canDownload={canDownload}
            actionError={actionError ?? error}
            onTranslate={handleTranslate}
            onViewProgress={handleViewProgress}
            onPreview={handlePreview}
            onDownload={handleDownload}
            onModeChange={setSelectedMode}
            agentRun={agentRun}
            agentBusy={agentBusy}
            agentError={agentError}
            onQuickExplain={() => void handleAgentQuickRun(t("community.detail.quickExplain"))}
            onQuickSummary={() => void handleAgentQuickRun(t("community.detail.quickSummary"))}
            onCitationOpen={(citation) => void handleAgentCitationOpen(citation)}
          />
        </section>
      </div>
    </div>
  )
}
