import { useEffect, useMemo, useRef, useState, type ReactNode } from "react"
import {
  Bookmark,
  Download,
  ExternalLink,
  Eye,
  FileText,
  Github,
  Languages,
  LoaderCircle,
  MessageSquareText,
  Trash2,
} from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { API_BASE_URL } from "@/api-base"
import { createCommunityPaperDownloadSession } from "@/features/community-paper/services/community-paper-api"
import {
  loadPdfHoverPreview,
  preloadPdfHoverPreviewRenderer,
  type PdfHoverPreviewImage,
} from "@/features/community-paper/services/pdf-hover-preview"
import { prefetchCommunityPaperDetail } from "@/lib/community-api"
import { preloadPaperPreviewEnhancer } from "@/lib/paper-preview-enhancer"
import type { CommunityPaper } from "@/types/community"
import { Button } from "@/ui/button/Button"
import { Pill } from "@/ui/pill/Pill"

interface PaperCardProps {
  paper: CommunityPaper
  onDelete?: (paper: CommunityPaper) => void
  deleting?: boolean
}

interface PdfPreviewFrameProps {
  imageUrl: string | null
  pdfDocumentUrl: string | null
  unavailableIcon: ReactNode
  placeholderTone: "neutral" | "accent"
  testId: string
}

function resolveDownloadFilename(
  response: Response,
  fallbackFilename: string,
) {
  const contentDisposition = response.headers.get("content-disposition") ?? ""
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      return utf8Match[1]
    }
  }

  const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/i)
  return filenameMatch?.[1] ?? fallbackFilename
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

const PREVIEW_INSPECTOR_WIDTH = 600
const PREVIEW_INSPECTOR_HEIGHT = 800
const PREVIEW_INSPECTOR_OFFSET = 18
const PREVIEW_INSPECTOR_TARGET_ZOOM = 4
const PREVIEW_WARMUP_DELAY_MS = 80

type IdleCallbackHandle = number

type IdleCallbackFn = (deadline: { didTimeout: boolean; timeRemaining: () => number }) => void

type IdleSchedulerWindow = Window & {
  requestIdleCallback?: (callback: IdleCallbackFn, options?: { timeout: number }) => IdleCallbackHandle
  cancelIdleCallback?: (handle: IdleCallbackHandle) => void
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function PdfPreviewFrame({
  imageUrl,
  pdfDocumentUrl,
  unavailableIcon,
  placeholderTone,
  testId,
}: PdfPreviewFrameProps) {
  const [loadedImageUrl, setLoadedImageUrl] = useState<string | null>(null)
  const [inspectorAnchor, setInspectorAnchor] = useState<{ x: number; y: number; frameHeight: number } | null>(null)
  const [pdfInspectorImage, setPdfInspectorImage] = useState<PdfHoverPreviewImage | null>(null)
  const [inspectorLoading, setInspectorLoading] = useState(false)
  const warmupScheduledRef = useRef(false)
  const warmupTimeoutRef = useRef<number | null>(null)
  const warmupIdleHandleRef = useRef<IdleCallbackHandle | null>(null)
  const loaded = Boolean(imageUrl) && loadedImageUrl === imageUrl
  const frameTestId = testId.replace(/-image$/, "-frame")
  const inspectorTestId = testId.replace(/-image$/, "-inspector")
  const inspectorImageTestId = testId.replace(/-image$/, "-inspector-image")
  const inspectorLoadingTestId = testId.replace(/-image$/, "-inspector-loading")

  useEffect(
    () => () => {
      if (typeof window === "undefined") {
        return
      }

      const idleWindow = window as IdleSchedulerWindow
      if (warmupTimeoutRef.current !== null) {
        window.clearTimeout(warmupTimeoutRef.current)
      }
      if (warmupIdleHandleRef.current !== null && idleWindow.cancelIdleCallback) {
        idleWindow.cancelIdleCallback(warmupIdleHandleRef.current)
      }
    },
    [],
  )

  function updateInspectorPosition(event: React.PointerEvent<HTMLDivElement>) {
    if (!loaded) {
      return
    }

    const rect = event.currentTarget.getBoundingClientRect()
    const width = rect.width || event.currentTarget.clientWidth || 320
    const height = rect.height || event.currentTarget.clientHeight || 240
    const x = clamp((event.clientX - rect.left) / width, 0, 1)
    const y = clamp((event.clientY - rect.top) / height, 0, 1)

    setInspectorAnchor({ x, y, frameHeight: height })
  }

  function resetInspector() {
    setInspectorAnchor(null)
  }

  function ensureInspectorPreview() {
    if (!pdfDocumentUrl || pdfInspectorImage || inspectorLoading) {
      return
    }

    setInspectorLoading(true)
    void loadPdfHoverPreview(pdfDocumentUrl)
      .then((nextPreview) => {
        setPdfInspectorImage(nextPreview)
      })
      .catch(() => {
        setPdfInspectorImage(null)
      })
      .finally(() => {
        setInspectorLoading(false)
      })
  }

  function warmInspectorPreviewInBackground() {
    if (!pdfDocumentUrl || warmupScheduledRef.current || typeof window === "undefined") {
      return
    }

    warmupScheduledRef.current = true

    const idleWindow = window as IdleSchedulerWindow
    const runWarmup = () => {
      void preloadPdfHoverPreviewRenderer()
      void loadPdfHoverPreview(pdfDocumentUrl)
    }

    warmupTimeoutRef.current = window.setTimeout(() => {
      if (idleWindow.requestIdleCallback) {
        warmupIdleHandleRef.current = idleWindow.requestIdleCallback(() => {
          runWarmup()
        }, { timeout: 400 })
        return
      }

      runWarmup()
    }, PREVIEW_WARMUP_DELAY_MS)
  }

  const previewImageWidth = pdfInspectorImage?.width ?? PREVIEW_INSPECTOR_WIDTH * PREVIEW_INSPECTOR_TARGET_ZOOM
  const previewImageHeight =
    pdfInspectorImage?.height ?? PREVIEW_INSPECTOR_HEIGHT * PREVIEW_INSPECTOR_TARGET_ZOOM
  const inspectorOffsetX = inspectorAnchor
    ? clamp(
      inspectorAnchor.x * previewImageWidth - PREVIEW_INSPECTOR_WIDTH / 2,
      0,
      Math.max(previewImageWidth - PREVIEW_INSPECTOR_WIDTH, 0),
    )
    : 0
  const inspectorOffsetY = inspectorAnchor
    ? clamp(
      inspectorAnchor.y * previewImageHeight - PREVIEW_INSPECTOR_HEIGHT / 2,
      0,
      Math.max(previewImageHeight - PREVIEW_INSPECTOR_HEIGHT, 0),
    )
    : 0
  const inspectorTop = inspectorAnchor
    ? clamp(
      inspectorAnchor.y * inspectorAnchor.frameHeight - PREVIEW_INSPECTOR_HEIGHT / 2,
      -(PREVIEW_INSPECTOR_HEIGHT - inspectorAnchor.frameHeight),
      0,
    )
    : 0

  return (
    <div
      data-testid={frameTestId}
      className="relative flex h-full min-h-[240px] overflow-visible"
      onPointerEnter={(event) => {
        void preloadPdfHoverPreviewRenderer()
        ensureInspectorPreview()
        updateInspectorPosition(event)
      }}
      onPointerMove={updateInspectorPosition}
      onPointerLeave={resetInspector}
      onPointerCancel={resetInspector}
    >
      <div className="relative flex h-full min-h-[240px] w-full overflow-hidden rounded-sm border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] shadow-[0_18px_48px_-34px_rgba(8,23,38,0.4)] transition-transform duration-200">
        {imageUrl ? (
          <img
            data-testid={testId}
            src={imageUrl}
            alt=""
            loading="lazy"
            className={`absolute inset-0 h-full w-full bg-white object-cover transition-opacity duration-300 ${loaded ? "opacity-100" : "opacity-0"}`}
            onLoad={() => {
              setLoadedImageUrl(imageUrl)
              warmInspectorPreviewInBackground()
            }}
            onError={() => {
              setLoadedImageUrl(null)
              resetInspector()
            }}
          />
        ) : null}

        <div
          className={`pointer-events-none absolute inset-0 p-4 transition-opacity duration-300 ${loaded ? "opacity-0" : "opacity-100"}`}
        >
          <div className={`mb-3 h-2.5 w-3/4 rounded-full ${placeholderTone === "accent" ? "bg-[color:var(--px-shell-accent-soft)]" : "bg-[color:var(--px-shell-line)]"}`} />
          <div className="mb-2 h-1.5 w-full rounded-full bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_70%,var(--px-shell-line))]" />
          <div className="mb-2 h-1.5 w-full rounded-full bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_70%,var(--px-shell-line))]" />
          <div className="mb-6 h-1.5 w-5/6 rounded-full bg-[color:color-mix(in_srgb,var(--px-shell-panel-strong)_70%,var(--px-shell-line))]" />
          <div className={`mt-auto h-[58%] rounded-sm ${placeholderTone === "accent" ? "bg-[color:color-mix(in_srgb,var(--px-shell-accent-soft)_70%,white)]" : "bg-[color:var(--px-shell-panel)]"}`} />
        </div>

        {!imageUrl ? (
          <div className="absolute inset-0 flex items-center justify-center bg-[color:var(--px-shell-panel)]/60 text-[color:var(--px-shell-accent)]">
            {unavailableIcon}
          </div>
        ) : null}
      </div>

      {loaded && inspectorAnchor ? (
        <div
          data-testid={inspectorTestId}
          aria-hidden="true"
          className="pointer-events-none absolute z-[5] hidden overflow-hidden rounded-md border border-white/65 bg-[color:var(--px-shell-panel)] shadow-[0_32px_72px_-26px_rgba(4,11,26,0.62),0_0_0_1px_rgba(67,205,255,0.18)] ring-1 ring-[color:var(--px-shell-accent)]/28 md:block"
          style={{
            width: `${PREVIEW_INSPECTOR_WIDTH}px`,
            height: `${PREVIEW_INSPECTOR_HEIGHT}px`,
            right: `calc(100% + ${PREVIEW_INSPECTOR_OFFSET}px)`,
            top: `${inspectorTop}px`,
          }}
        >
          <div className="absolute inset-3 overflow-hidden rounded-sm border border-[color:var(--px-shell-line)] bg-white shadow-inner">
            {pdfInspectorImage ? (
              <img
                data-testid={inspectorImageTestId}
                src={pdfInspectorImage.dataUrl}
                alt=""
                className="absolute left-0 top-0 max-w-none"
                style={{
                  width: `${pdfInspectorImage.width}px`,
                  height: `${pdfInspectorImage.height}px`,
                  transform: `translate(${-inspectorOffsetX}px, ${-inspectorOffsetY}px)`,
                }}
              />
            ) : inspectorLoading ? (
              <div
                data-testid={inspectorLoadingTestId}
                className="absolute inset-0 animate-pulse bg-[linear-gradient(135deg,rgba(232,240,248,0.94),rgba(248,252,255,0.98))]"
              >
                <div className="absolute inset-x-6 top-8 h-3 rounded-full bg-[color:var(--px-shell-line)]" />
                <div className="absolute inset-x-6 top-15 h-2.5 rounded-full bg-[color:var(--px-shell-line)]/85" />
                <div className="absolute inset-x-6 top-21 h-2.5 rounded-full bg-[color:var(--px-shell-line)]/75" />
                <div className="absolute inset-x-6 top-31 h-3 rounded-full bg-[color:var(--px-shell-accent-soft)]" />
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  )
}

function formatAuthors(authors: unknown[], fallback: string) {
  if (!authors.length) {
    return fallback
  }

  return authors
    .slice(0, 3)
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

function PreviewLink({
  to,
  label,
  testId,
  children,
  onIntent,
}: {
  to: string | null
  label: string
  testId: string
  children: ReactNode
  onIntent: () => void
}) {
  if (!to) {
    return (
      <div data-testid={testId} className="flex h-full flex-col gap-2">
        {children}
      </div>
    )
  }

  return (
    <Link
      to={to}
      aria-label={label}
      data-testid={testId}
      onMouseEnter={onIntent}
      onFocus={onIntent}
      onPointerDown={onIntent}
      className="group flex h-full flex-col gap-2 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/25"
    >
      {children}
    </Link>
  )
}

export function PaperCard({ paper, onDelete, deleting = false }: PaperCardProps) {
  const { t } = useTranslation()
  const [sourceDownloadPending, setSourceDownloadPending] = useState(false)
  const [downloadPending, setDownloadPending] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  function prefetchDetailNavigation() {
    void prefetchCommunityPaperDetail(paper.id)
    void preloadPaperPreviewEnhancer()
    void preloadPdfHoverPreviewRenderer()
  }

  const sourcePdfUrl =
    paper.source === "arxiv" || Boolean(paper.assets?.source_archive) || Boolean(paper.community_selected_task_id)
      ? `${API_BASE_URL}/api/papers/${paper.id}/source-thumbnail`
      : null
  const translatedPdfUrl =
    paper.trans_status === "completed" &&
      (Boolean(paper.assets?.translated_pdf) || Boolean(paper.community_selected_task_id))
      ? `${API_BASE_URL}/api/papers/${paper.id}/translated-thumbnail`
      : null
  const sourcePdfDocumentUrl =
    paper.source === "arxiv" || Boolean(paper.assets?.source_archive) || Boolean(paper.community_selected_task_id)
      ? `${API_BASE_URL}/api/papers/${paper.id}/source-pdf`
      : null
  const translatedPdfDocumentUrl =
    paper.trans_status === "completed" &&
      (Boolean(paper.assets?.translated_pdf) || Boolean(paper.community_selected_task_id))
      ? `${API_BASE_URL}/api/papers/${paper.id}/translated-pdf`
      : null
  const sourceDownloadUrl = sourcePdfDocumentUrl
    ? `${API_BASE_URL}/api/papers/${paper.id}/source-download`
    : null
  const arxivUrl = paper.arxiv_url ?? (paper.arxiv_id ? `https://arxiv.org/abs/${paper.arxiv_id}` : null)
  const githubUrl = paper.github_url ?? null

  const authorsLabel = useMemo(
    () => formatAuthors(paper.authors, t("community.card.authorsUnavailable")),
    [paper.authors, t],
  )
  const abstractText =
    paper.abstract_raw || paper.abstract_translated || t("community.card.abstractPlaceholder")
  const detailHref = `/paper/${paper.id}`

  async function handleSourceDownload() {
    if (!sourceDownloadUrl || sourceDownloadPending) {
      return
    }

    try {
      setActionError(null)
      setSourceDownloadPending(true)
      const response = await fetch(sourceDownloadUrl)
      if (!response.ok) {
        throw new Error(`Source download failed: ${response.status}`)
      }

      const blob = await response.blob()
      const blobUrl = window.URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = blobUrl
      link.download = resolveDownloadFilename(
        response,
        `${paper.arxiv_id ?? paper.id}-source.pdf`,
      )
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(blobUrl)
    } catch (downloadError) {
      setActionError(extractActionErrorMessage(downloadError) ?? t("community.actions.downloadError"))
    } finally {
      setSourceDownloadPending(false)
    }
  }

  async function handleTranslatedDownload() {
    if (downloadPending || !translatedPdfDocumentUrl) {
      return
    }

    try {
      setActionError(null)
      setDownloadPending(true)
      const session = await createCommunityPaperDownloadSession(paper.id)
      const downloadUrl = session.download_url.startsWith("http")
        ? session.download_url
        : `${API_BASE_URL}${session.download_url}`
      window.open(downloadUrl, "_blank", "noopener,noreferrer")
    } catch (downloadError) {
      setActionError(extractActionErrorMessage(downloadError) ?? t("community.actions.downloadError"))
    } finally {
      setDownloadPending(false)
    }
  }

  return (
    <article className="grid gap-5 rounded-md border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-5 shadow-[var(--px-shell-shadow)] transition-colors duration-200 xl:grid-cols-[minmax(0,0.85fr)_minmax(340px,1.15fr)]">
      <div className="flex min-w-0 flex-col justify-between">
        <div className="space-y-4">
          <div className="flex items-start justify-between gap-4">
            <div className="flex flex-wrap gap-2">
              {paper.categories.slice(0, 3).map((category) => (
                <Pill key={category} tone="accent" className="px-3 py-1 text-[10px]">
                  {category}
                </Pill>
              ))}
              {paper.categories.length === 0 ? (
                <Pill tone="accent" className="px-3 py-1 text-[10px]">
                  {t("community.card.categoriesUnavailable")}
                </Pill>
              ) : null}
            </div>

            {onDelete ? (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                disabled={deleting}
                onClick={() => onDelete(paper)}
                className="h-9 w-9 text-[color:var(--px-shell-danger)] hover:bg-[color:var(--px-shell-danger-soft)]"
                aria-label={t("community.admin.deleteAction")}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            ) : (
              <Bookmark className="h-5 w-5 shrink-0 text-[color:var(--px-shell-muted)]/45" />
            )}
          </div>

          <div className="space-y-3">
            <Link
              to={detailHref}
              onMouseEnter={prefetchDetailNavigation}
              onFocus={prefetchDetailNavigation}
              onPointerDown={prefetchDetailNavigation}
              className="inline-flex max-w-full rounded-sm outline-none transition-colors duration-200 hover:text-[color:var(--px-shell-accent)] focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/25"
            >
              <h3 className="text-lg font-bold leading-tight text-[color:var(--px-shell-ink)] md:text-[1.28rem]">
                {paper.title}
              </h3>
            </Link>

            <p className="select-text text-sm font-semibold text-[color:var(--px-shell-ink)]/88">
              {authorsLabel}
            </p>

            <p className="select-text text-sm leading-7 text-[color:var(--px-shell-muted)]">{abstractText}</p>
          </div>

          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {sourceDownloadUrl ? (
                <Button
                  type="button"
                  variant="action"
                  size="chip"
                  disabled={sourceDownloadPending}
                  onClick={() => void handleSourceDownload()}
                  aria-label={t("community.card.action.downloadSourcePdf")}
                  className="min-w-fit"
                >
                  {sourceDownloadPending ? (
                    <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Download className="h-3.5 w-3.5" />
                  )}
                  {sourceDownloadPending
                    ? t("community.card.action.preparingTranslatedPdf")
                    : t("community.card.action.downloadSourcePdf")}
                </Button>
              ) : null}

              {translatedPdfDocumentUrl ? (
                <Button
                  type="button"
                  variant="action"
                  size="chip"
                  disabled={downloadPending}
                  onClick={() => void handleTranslatedDownload()}
                  aria-label={t("community.card.action.downloadTranslatedPdf")}
                  className="min-w-fit"
                >
                  {downloadPending ? (
                    <LoaderCircle className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Languages className="h-3.5 w-3.5" />
                  )}
                  {downloadPending
                    ? t("community.card.action.preparingTranslatedPdf")
                    : t("community.card.action.downloadTranslatedPdf")}
                </Button>
              ) : null}

              {arxivUrl ? (
                <Button
                  asChild
                  variant="action"
                  size="chip"
                  className="min-w-fit"
                >
                  <a
                    href={arxivUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={t("community.card.action.openArxiv")}
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    {t("community.card.action.openArxiv")}
                  </a>
                </Button>
              ) : null}

              {githubUrl ? (
                <Button
                  asChild
                  variant="action"
                  size="chip"
                  className="min-w-fit"
                >
                  <a
                    href={githubUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={t("community.card.action.openGithub")}
                  >
                    <Github className="h-3.5 w-3.5" />
                    {t("community.card.action.openGithub")}
                  </a>
                </Button>
              ) : null}
            </div>

            {actionError ? (
              <p className="text-xs font-medium text-[color:var(--px-shell-danger)]">{actionError}</p>
            ) : null}
          </div>
        </div>

        <div className="mt-5 flex items-center justify-between border-t border-[color:var(--px-shell-line)] pt-4">
          <div className="flex items-center gap-4 text-xs text-[color:var(--px-shell-muted)] md:text-sm">
            <span className="flex items-center gap-1.5">
              <Eye className="h-4 w-4" />
              {paper.view_count || 0}
            </span>
            <span className="flex items-center gap-1.5">
              <MessageSquareText className="h-4 w-4" />
              {paper.comment_count || 0}
            </span>
          </div>
        </div>
      </div>

      <div className="grid min-h-[280px] grid-cols-2 gap-4">
        <PreviewLink
          to={detailHref}
          label={t("community.detail.originalSource")}
          testId="paper-card-source-preview-link"
          onIntent={prefetchDetailNavigation}
        >
          <PdfPreviewFrame
            imageUrl={sourcePdfUrl}
            pdfDocumentUrl={sourcePdfDocumentUrl}
            unavailableIcon={<FileText className="h-7 w-7" />}
            placeholderTone="neutral"
            testId="paper-card-source-preview-image"
          />
          <span className="px-1 text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
            {paper.source === "arxiv" ? t("community.detail.originalSource") : t("community.detail.sourceTitle")}
          </span>
        </PreviewLink>

        <PreviewLink
          to={translatedPdfUrl ? detailHref : null}
          label={t("community.detail.mode.translatedPdf")}
          testId="paper-card-translated-preview-link"
          onIntent={prefetchDetailNavigation}
        >
          <PdfPreviewFrame
            imageUrl={translatedPdfUrl}
            pdfDocumentUrl={translatedPdfDocumentUrl}
            unavailableIcon={<Languages className="h-7 w-7" />}
            placeholderTone="accent"
            testId="paper-card-translated-preview-image"
          />
          <span className="px-1 text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
            {t("community.detail.mode.translatedPdf")}
          </span>
        </PreviewLink>
      </div>
    </article>
  )
}
