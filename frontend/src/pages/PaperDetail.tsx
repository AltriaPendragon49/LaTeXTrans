import {
  ArrowLeft,
  Clock3,
  Eye,
  Heart,
  Languages,
  Link2,
  MessageSquare,
  ScrollText,
  Star,
} from "lucide-react"
import { Fragment, type ReactNode, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Link, useNavigate, useParams } from "react-router-dom"

import { PaperActionShell } from "@/components/community/PaperActionShell"
import { PaperDetailSkeleton } from "@/components/community/PaperDetailSkeleton"
import { PaperPreviewReader } from "@/components/community/PaperPreviewReader"
import { PaperStatusBadge } from "@/components/community/PaperStatusBadge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { createCommunityPaperDownloadSession, translateCommunityPaper } from "@/lib/community-api"
import { API_BASE_URL } from "@/api-base"
import { usePaperDetail } from "@/hooks/use-paper-detail"
import { useStore } from "@/store/useStore"
import type { PaperAssetSummary } from "@/types/community"

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

const ABSTRACT_URL_PATTERN = /\[<(https?:\/\/[^>\s]+)>\]|(https?:\/\/[^\s<>\])]+)/g

function renderLinkedText(text: string) {
  const nodes: Array<ReactNode | string> = []
  let lastIndex = 0

  for (const match of text.matchAll(ABSTRACT_URL_PATTERN)) {
    const index = match.index ?? 0
    const fullMatch = match[0]
    const bracketedUrl = match[1]
    const bareUrl = match[2]
    const url = bracketedUrl || bareUrl

    if (!url) {
      continue
    }

    if (index > lastIndex) {
      nodes.push(text.slice(lastIndex, index))
    }

    const anchor = (
      <a
        key={`${url}-${index}`}
        href={url}
        target="_blank"
        rel="noreferrer noopener"
        className="text-sky-600 underline decoration-sky-400/60 underline-offset-4 hover:text-sky-500 dark:text-sky-300 dark:hover:text-sky-200"
      >
        {url}
      </a>
    )

    if (bracketedUrl) {
      nodes.push(
        <Fragment key={`wrapped-${url}-${index}`}>
          [
          {anchor}
          ]
        </Fragment>,
      )
    } else {
      nodes.push(anchor)
    }

    lastIndex = index + fullMatch.length
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex))
  }

  return nodes
}

function formatDetailDate(
  value: string | null | undefined,
  locale: string,
  fallback: string,
) {
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

export default function PaperDetailPage() {
  const { i18n, t } = useTranslation()
  const navigate = useNavigate()
  const previewRef = useRef<HTMLDivElement>(null)
  const { paperId } = useParams<{ paperId: string }>()
  const { paper, preview, readerState, loading, error, notFound } = usePaperDetail(paperId)
  const { config, loadUserSettings, setTaskId, setArxivId } = useStore()
  const [actionError, setActionError] = useState<string | null>(null)

  if (loading) {
    return (
      <div className="min-h-full bg-[var(--shell-bg)] px-4 py-6 text-[var(--shell-text)] transition-colors sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-[2200px]">
          <PaperDetailSkeleton />
        </div>
      </div>
    )
  }

  if (error && !notFound && !paper) {
    return (
      <div className="min-h-full bg-[var(--shell-bg)] px-4 py-6 text-[var(--shell-text)] transition-colors sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl rounded-[32px] border border-rose-500/20 bg-rose-500/5 px-6 py-14 text-center">
          <h1 className="text-3xl font-semibold text-rose-950 dark:text-white">{t("community.detail.errorTitle")}</h1>
          <p className="mt-3 text-sm text-rose-900/80 dark:text-slate-300">{t("community.detail.errorDescription")}</p>
          <p className="mt-4 text-xs text-rose-800/80 dark:text-slate-400">{error}</p>
          <Button asChild variant="outline" className="mt-6 rounded-2xl border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-heading)]">
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
          <h1 className="text-3xl font-semibold text-[var(--shell-heading)]">{t("community.detail.notFoundTitle")}</h1>
          <p className="mt-3 text-sm text-[var(--shell-text-muted)]">{t("community.detail.notFoundDescription")}</p>
          <Button asChild variant="outline" className="mt-6 rounded-2xl border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-heading)]">
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
    activePaper.abstract_translated || activePaper.abstract_raw || t("community.detail.abstractUnavailable")
  const assetLabel = activePaper.latest_asset
    ? `${getAssetTypeLabel(activePaper.latest_asset.asset_type, t)} · ${activePaper.latest_asset.file_name}`
    : t("community.card.assetUnavailable")
  const canTranslate = ["not_started", "failed"].includes(activePaper.trans_status)
  const canViewProgress = Boolean(
    activePaper.community_selected_task_id && ["queued", "processing"].includes(activePaper.trans_status),
  )
  const canDownload = Boolean(
    activePaper.assets?.translated_pdf ||
      activePaper.latest_asset?.asset_type === "translated_pdf" ||
      activePaper.trans_status === "completed",
  )
  const detailMetaItems = [
    {
      key: "views",
      icon: Eye,
      label: String(activePaper.view_count ?? 0),
      ariaLabel: t("community.card.views", { count: activePaper.view_count ?? 0 }),
    },
    {
      key: "likes",
      icon: Heart,
      label: String(activePaper.like_count ?? 0),
      ariaLabel: t("community.card.likes", { count: activePaper.like_count ?? 0 }),
    },
    {
      key: "favorites",
      icon: Star,
      label: String(activePaper.favorite_count ?? 0),
      ariaLabel: t("community.card.favorites", { count: activePaper.favorite_count ?? 0 }),
    },
    {
      key: "comments",
      icon: MessageSquare,
      label: String(activePaper.comment_count ?? 0),
      ariaLabel: t("community.card.comments", { count: activePaper.comment_count ?? 0 }),
    },
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

  function handlePreview() {
    const target = previewRef.current ?? document.getElementById("paper-preview-reader")
    target?.scrollIntoView({ behavior: "smooth", block: "start" })
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
    <div className="min-h-full bg-[var(--shell-bg)] px-4 py-6 text-[var(--shell-text)] transition-colors sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-[2560px] space-y-4">
        <Button
          asChild
          variant="ghost"
          className="min-h-11 rounded-full border border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-4 text-[var(--shell-heading)] hover:bg-[var(--shell-pill-hover)]"
        >
          <Link to="/">
            <ArrowLeft className="h-4 w-4" />
            {t("community.detail.backToFeed")}
          </Link>
        </Button>

        <section className="rounded-[28px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-5 shadow-[var(--shell-panel-shadow-strong)] sm:p-7">
          <div className="flex flex-wrap gap-2">
            <PaperStatusBadge kind="community" value={activePaper.community_status} />
            <PaperStatusBadge kind="translation" value={activePaper.trans_status} />
            {activePaper.arxiv_id ? (
              <Badge className="rounded-full border border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-[var(--shell-text)]">
                {t("community.detail.arxivBadge", { value: activePaper.arxiv_id })}
              </Badge>
            ) : null}
          </div>

          <div className="mt-5 space-y-2.5">
            <h1 className="max-w-5xl text-balance text-[2.2rem] font-semibold tracking-tight text-[var(--shell-heading)] sm:text-[3rem]">
              {activePaper.title}
            </h1>
            <p className="max-w-3xl text-base text-[var(--shell-text-soft)]">{authorsLabel}</p>
            <p className="text-xs uppercase tracking-[0.18em] text-[var(--shell-text-muted)]">
              {activePaper.categories.length
                ? activePaper.categories.join(" · ")
                : t("community.card.categoriesUnavailable")}
            </p>
          </div>

          <div
            data-testid="paper-detail-header-metadata"
            className="mt-5 flex flex-wrap items-center gap-2 border-t border-[color:var(--shell-border-strong)] pt-4"
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

          <div className="mt-8 space-y-6">
            <div
              data-testid="paper-detail-top-panels"
              className="grid gap-6 xl:grid-cols-[minmax(0,1.95fr)_minmax(520px,1.15fr)] 2xl:grid-cols-[minmax(0,2.05fr)_minmax(560px,1.2fr)]"
            >
              <Card
                data-testid="paper-detail-reader-panel"
                className="flex min-h-[720px] flex-col overflow-hidden rounded-[24px] border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] text-[var(--shell-text)] shadow-none xl:h-[calc(100vh-11rem)] xl:min-h-[820px] xl:max-h-[1320px]"
              >
                <CardHeader className="pb-4">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <ScrollText className="h-4 w-4 text-[var(--shell-icon)]" />
                    {t("community.detail.readerTitle")}
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex min-h-0 flex-1 flex-col">
                  <PaperPreviewReader
                    ref={previewRef}
                    paperId={activePaper.id}
                    initialPreview={preview}
                    readerState={readerState}
                  />
                </CardContent>
              </Card>

              <Card className="flex min-h-[720px] flex-col overflow-hidden rounded-[24px] border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] text-[var(--shell-text)] shadow-none xl:h-[calc(100vh-11rem)] xl:min-h-[820px] xl:max-h-[1320px]">
                <CardHeader className="pb-4">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Languages className="h-4 w-4 text-[var(--shell-icon)]" />
                    {t("community.detail.workspaceTitle")}
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex min-h-0 flex-1 flex-col">
                  <div className="flex min-h-0 flex-1 flex-col justify-between rounded-[20px] border border-dashed border-[color:var(--shell-border-strong)] bg-[var(--shell-bg)]/35 p-5">
                    <div className="space-y-4 overflow-y-auto">
                      <p className="text-sm leading-7 text-[var(--shell-text-soft)]">
                        {t("community.detail.workspaceDescription")}
                      </p>
                      <div className="rounded-2xl border border-[color:var(--shell-border-strong)] bg-[var(--shell-pill)] p-4">
                        <p className="text-xs uppercase tracking-[0.18em] text-[var(--shell-text-muted)]">
                          {t("community.detail.latestAsset")}
                        </p>
                        <p className="mt-2 text-sm leading-6 text-[var(--shell-heading)]">{assetLabel}</p>
                      </div>
                    </div>
                    <div className="mt-5 rounded-2xl border border-[color:var(--shell-border-strong)] bg-[var(--shell-pill)] p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-[var(--shell-text-muted)]">
                        {t("community.detail.workspaceNextTitle")}
                      </p>
                      <p className="mt-2 text-sm leading-6 text-[var(--shell-text-soft)]">
                        {t("community.detail.workspaceNextDescription")}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1.15fr)_360px]">
              <div className="space-y-6">
                <Card className="rounded-[24px] border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] text-[var(--shell-text)] shadow-none">
                  <CardHeader className="pb-4">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      <ScrollText className="h-4 w-4 text-[var(--shell-icon)]" />
                      {t("community.detail.abstractTitle")}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4 text-sm leading-7 text-[var(--shell-text-soft)]">
                    <p>{renderLinkedText(abstractText)}</p>
                  </CardContent>
                </Card>
              </div>

              <div className="space-y-6">
                <PaperActionShell
                  onTranslate={handleTranslate}
                  onViewProgress={handleViewProgress}
                  onPreview={handlePreview}
                  onDownload={handleDownload}
                  canTranslate={canTranslate}
                  canViewProgress={canViewProgress}
                  canDownload={canDownload}
                />

                {error || actionError ? (
                  <p className="text-xs text-[var(--shell-text-muted)]">{actionError ?? error}</p>
                ) : null}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
