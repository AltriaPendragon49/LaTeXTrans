import { useMemo, useState, type ReactNode } from "react"
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

function PdfPreviewFrame({
  imageUrl,
  unavailableIcon,
  placeholderTone,
  testId,
}: PdfPreviewFrameProps) {
  const [loadedImageUrl, setLoadedImageUrl] = useState<string | null>(null)
  const [isHovered, setIsHovered] = useState(false)
  const loaded = Boolean(imageUrl) && loadedImageUrl === imageUrl
  const frameTestId = testId.replace(/-image$/, "-frame")

  return (
    <div
      data-testid={frameTestId}
      /* 修改 1：移除 h-full 和 min-h，加入 w-full 和标准 A4 比例 aspect-[210/297] */
      className="relative flex w-full aspect-[210/297] overflow-visible"
      onPointerEnter={() => setIsHovered(true)}
      onPointerLeave={() => setIsHovered(false)}
      onPointerCancel={() => setIsHovered(false)}
      onFocus={() => setIsHovered(true)}
      onBlur={() => setIsHovered(false)}
    >
      <div
        data-testid={testId.replace(/-image$/, "-surface")}
        /* 修改 2：保持 h-full 让它填满上面定义的 A4 比例容器，移除 min-h */
        className={`relative z-0 flex h-full w-full origin-center overflow-hidden rounded-sm border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] shadow-[0_18px_48px_-34px_rgba(8,23,38,0.4)] transition-[transform,box-shadow] duration-200 ${isHovered ? "z-10 scale-[1.40] shadow-[0_34px_82px_-28px_rgba(8,23,38,0.62)]" : "scale-100"}
`}
      >
        {imageUrl ? (
          <img
            data-testid={testId}
            src={imageUrl}
            alt=""
            loading="lazy"
            /* 修改 3：额外留出纵向呼吸空间，尽量完整展示第一页内容 */
            className={`absolute inset-0 h-full w-full bg-white object-contain object-center px-1 py-2 transition-opacity duration-300 ${loaded ? "opacity-100" : "opacity-0"}`}
            onLoad={() => {
              setLoadedImageUrl(imageUrl)
            }}
            onError={() => {
              setLoadedImageUrl(null)
              setIsHovered(false)
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
      /* 修改 4：移除 h-full，让它自然贴合内部的 A4 比例容器 */
      <div data-testid={testId} className="flex flex-col gap-2">
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
      /* 修改 5：同样移除这里的 h-full */
      className="group flex flex-col gap-2 rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/25"
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
    <article className="grid gap-5 rounded-md border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-5 shadow-[var(--px-shell-shadow)] transition-colors duration-200 xl:grid-cols-[minmax(0,1.15fr)_minmax(280px,0.85fr)]">
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

            <p className="select-text text-sm leading-7 text-[color:var(--px-shell-muted)] line-clamp-3">
              {abstractText}
            </p>
          </div>

          <div className="space-y-2">
            <div className="flex w-full flex-row items-center gap-2 pb-1">
              {sourceDownloadUrl ? (
                <Button
                  type="button"
                  variant="action"
                  size="chip"
                  disabled={sourceDownloadPending}
                  onClick={() => void handleSourceDownload()}
                  aria-label={t("community.card.action.downloadSourcePdf")}
                  className="flex-1 min-w-0 px-2"
                >
                  {sourceDownloadPending ? (
                    <LoaderCircle className="h-3.5 w-3.5 shrink-0 animate-spin" />
                  ) : (
                    <Download className="h-3.5 w-3.5 shrink-0" />
                  )}
                  <span className="truncate">
                    {sourceDownloadPending
                      ? t("community.card.action.preparingTranslatedPdf")
                      : t("community.card.action.downloadSourcePdf")}
                  </span>
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
                  className="flex-1 min-w-0 px-2"
                >
                  {downloadPending ? (
                    <LoaderCircle className="h-3.5 w-3.5 shrink-0 animate-spin" />
                  ) : (
                    <Languages className="h-3.5 w-3.5 shrink-0" />
                  )}
                  <span className="truncate">
                    {downloadPending
                      ? t("community.card.action.preparingTranslatedPdf")
                      : t("community.card.action.downloadTranslatedPdf")}
                  </span>
                </Button>
              ) : null}

              {arxivUrl ? (
                <Button
                  asChild
                  variant="action"
                  size="chip"
                  className="flex-1 min-w-0 px-2"
                >
                  <a
                    href={arxivUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={t("community.card.action.openArxiv")}
                    className="flex w-full items-center justify-center gap-1.5"
                  >
                    <ExternalLink className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{t("community.card.action.openArxiv")}</span>
                  </a>
                </Button>
              ) : null}

              {githubUrl ? (
                <Button
                  asChild
                  variant="action"
                  size="chip"
                  className="flex-1 min-w-0 px-2"
                >
                  <a
                    href={githubUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={t("community.card.action.openGithub")}
                    className="flex w-full items-center justify-center gap-1.5"
                  >
                    <Github className="h-3.5 w-3.5 shrink-0" />
                    <span className="truncate">{t("community.card.action.openGithub")}</span>
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

      {/* 修改 6：加入 items-start 让右侧网格容器顶部对齐，彻底阻断向下延展 */}
      <div className="grid grid-cols-2 gap-4 items-start">
        <PreviewLink
          to={detailHref}
          label={t("community.detail.originalSource")}
          testId="paper-card-source-preview-link"
          onIntent={prefetchDetailNavigation}
        >
          <PdfPreviewFrame
            imageUrl={sourcePdfUrl}
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
