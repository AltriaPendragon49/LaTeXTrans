import { useEffect, useRef, useState } from "react"
import { ArrowLeft, ChevronDown, ChevronUp, Download, Heart, Info, Share2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link, useLocation } from "react-router-dom"
import { toast } from "sonner"

import { FavoritePicker } from "@/features/community-paper/components/FavoritePicker"
import { useIsMobile } from "@/hooks/use-mobile"
import { cn } from "@/lib/utils"
import type { PaperFavoriteFolderUpdateResponse } from "@/types/community"
import { Button } from "@/ui/button/Button"
import { Popover, PopoverContent, PopoverTrigger } from "@/ui/primitives/popover"
import { SegmentedControl } from "@/ui/segmented-control/SegmentedControl"
import type { CommunityPaper, CommunityPaperReaderMode } from "@/types/community"

interface PaperDetailHeaderProps {
  paper: CommunityPaper
  selectedMode: CommunityPaperReaderMode
  availableModes: CommunityPaperReaderMode[]
  authorsLabel: string
  canDownload: boolean
  likePending?: boolean
  liked?: boolean
  likeCount?: number
  onSelectMode: (mode: CommunityPaperReaderMode) => void
  onDownload: () => void
  onLikeToggle?: () => void
  onFavoriteStateChange?: (payload: PaperFavoriteFolderUpdateResponse) => void
  onMobileOpenAnalysis?: () => void
}

export function PaperDetailHeader({
  paper,
  selectedMode,
  availableModes,
  authorsLabel,
  canDownload,
  likePending = false,
  liked = false,
  likeCount = 0,
  onSelectMode,
  onDownload,
  onLikeToggle,
  onFavoriteStateChange,
  onMobileOpenAnalysis,
}: PaperDetailHeaderProps) {
  const { t } = useTranslation()
  const isMobile = useIsMobile()
  const location = useLocation()
  const shareTimerRef = useRef<number | null>(null)
  const [shareStatus, setShareStatus] = useState<"idle" | "copied">("idle")
  const [mobileToolbarCollapsed, setMobileToolbarCollapsed] = useState(() => isMobile)
  const wasMobileRef = useRef(isMobile)

  useEffect(() => {
    return () => {
      if (shareTimerRef.current !== null) {
        window.clearTimeout(shareTimerRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (isMobile && !wasMobileRef.current) {
      setMobileToolbarCollapsed(true)
    }
    if (!isMobile) {
      setMobileToolbarCollapsed(false)
    }
    wasMobileRef.current = isMobile
  }, [isMobile])

  const publishedAt = paper.arxiv_published_at ?? paper.official_published_at ?? paper.created_at
  const publishedLabel = publishedAt
    ? t("community.detail.publishedAt", {
        value: new Date(publishedAt).toLocaleDateString(),
      })
    : t("community.card.dateUnknown")

  const repositoryUrl = paper.github_url?.trim() || null
  const arxivUrl = paper.arxiv_id ? `https://arxiv.org/abs/${paper.arxiv_id}` : null
  const categoryLabel =
    paper.categories.length > 0
      ? paper.categories.join(" · ")
      : t("community.card.categoriesUnavailable")

  const modeItems = [
    {
      value: "source" as const,
      label: t("community.detail.mode.source"),
      testId: "paper-detail-mode-source",
    },
    {
      value: "translated_pdf" as const,
      label: t("community.detail.mode.translatedPdf"),
      disabled: !availableModes.includes("translated_pdf"),
      testId: "paper-detail-mode-translated-pdf",
    },
    {
      value: "bilingual_compare" as const,
      label: t("community.detail.mode.bilingualCompare"),
      disabled: !availableModes.includes("bilingual_compare"),
      testId: "paper-detail-mode-bilingual-compare",
    },
  ]

  async function handleShare() {
    const shareUrl =
      typeof window === "undefined"
        ? location.pathname
        : `${window.location.origin}${location.pathname}${location.search}${location.hash}`

    try {
      await navigator.clipboard.writeText(shareUrl)
      setShareStatus("copied")
      if (isMobile) {
        toast.success(t("community.detail.shareCopied"))
      }
      if (shareTimerRef.current !== null) {
        window.clearTimeout(shareTimerRef.current)
      }
      shareTimerRef.current = window.setTimeout(() => {
        setShareStatus("idle")
        shareTimerRef.current = null
      }, 1800)
    } catch {
      toast.error(t("community.detail.shareFailed", { defaultValue: "Unable to copy link" }))
    }
  }

  return (
    <nav
      data-testid="paper-detail-header"
      data-mobile-layout={isMobile ? "stacked" : "inline"}
      data-mobile-toolbar={isMobile ? (mobileToolbarCollapsed ? "collapsed" : "expanded") : undefined}
      className="sticky top-0 z-10 shrink-0 border-b border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)]/88 backdrop-blur-xl"
    >
      <div
        className={cn(
          isMobile
            ? mobileToolbarCollapsed
              ? "flex flex-col gap-1 px-2 py-1.5"
              : "flex flex-col gap-2 px-2 py-2"
            : "grid min-h-12 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 px-2 py-1.5 md:px-3",
        )}
      >
        <div
          data-testid={isMobile ? "paper-detail-header-mobile-actions" : undefined}
          className={cn(isMobile ? "flex items-center justify-between gap-2" : "contents")}
        >
          <div className={cn("flex items-center justify-start", !isMobile && "col-start-1")}>
            <Button
              asChild
              variant="ghost"
              size="icon"
              className={cn(
                "rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]",
                isMobile ? "h-9 w-9 rounded-[14px]" : "h-8 w-8",
              )}
            >
              <Link to="/" aria-label={t("community.detail.backToFeed")} title={t("community.detail.backToFeed")}>
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
          </div>

          <div className={cn("relative flex items-center justify-end gap-1", isMobile ? "min-w-0 flex-nowrap" : "col-start-3")}>
            <span
              data-testid="paper-detail-share-status"
              aria-live="polite"
              className={cn(
                "mr-1 text-[11px] font-medium text-[color:var(--px-shell-accent)] transition-opacity duration-200",
                isMobile
                  ? shareStatus === "copied"
                    ? "pointer-events-none absolute right-0 top-full z-20 mt-2 whitespace-nowrap rounded-full border border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-panel)] px-3 py-1 text-xs font-semibold shadow-[0_16px_34px_-24px_rgba(15,23,42,0.65)] opacity-100"
                    : "sr-only"
                  : shareStatus === "copied"
                    ? "opacity-100"
                    : "opacity-0",
              )}
            >
              {shareStatus === "copied" ? t("community.detail.shareCopied") : " "}
            </span>

            {isMobile && onMobileOpenAnalysis ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                data-testid="mobile-analysis-jump-button"
                onClick={onMobileOpenAnalysis}
                aria-label={t("community.detail.mobile.jumpToAnalysis", { defaultValue: "Open analysis" })}
                title={t("community.detail.mobile.jumpToAnalysis", { defaultValue: "Open analysis" })}
                className="h-8 min-h-0 rounded-full border border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)] px-2.5 text-[10px] font-extrabold tracking-[0.04em] text-[color:var(--px-shell-accent)] shadow-none hover:border-[color:var(--px-shell-accent-strong)] hover:bg-[color:var(--px-shell-accent)] hover:text-white"
              >
                <span>{t("community.detail.mobile.jumpToAnalysis", { defaultValue: "Open analysis" })}</span>
              </Button>
            ) : null}

            <Button
              type="button"
              variant="ghost"
              disabled={likePending}
              onClick={onLikeToggle}
              aria-label={liked ? t("community.likes.action.active") : t("community.likes.action.idle")}
              title={liked ? t("community.likes.action.active") : t("community.likes.action.idle")}
              aria-pressed={liked}
              className={cn(
                "border px-2.5 font-medium tracking-normal transition-colors",
                liked
                  ? "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)]"
                  : "border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]",
                isMobile ? "h-9 gap-1 rounded-[14px] px-2 text-[10px]" : "h-8 gap-1.5 rounded-[10px] text-[11px]",
              )}
            >
              <Heart className={`h-3.5 w-3.5 ${liked ? "fill-current" : ""}`} />
              <span className="min-w-[1ch] text-center tabular-nums">{likeCount}</span>
            </Button>

            <FavoritePicker
              paperId={paper.id}
              favoriteCount={paper.favorite_count ?? 0}
              viewerState={paper.viewer_state}
              variant="icon"
              onFavoriteStateChange={onFavoriteStateChange}
              className={isMobile ? "h-9 w-9 rounded-[14px]" : ""}
            />

            <Button
              type="button"
              variant="ghost"
              size="icon"
              disabled={!canDownload}
              onClick={onDownload}
              aria-label={t("community.card.action.downloadTranslatedPdf")}
              title={t("community.card.action.downloadTranslatedPdf")}
              className={cn(
                "rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]",
                isMobile ? "h-9 w-9 rounded-[14px]" : "h-8 w-8",
              )}
            >
              <Download className="h-4 w-4" />
            </Button>

            <Popover>
              <PopoverTrigger asChild>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  aria-label={t("community.detail.infoAction")}
                  title={t("community.detail.infoAction")}
                  className={cn(
                    "rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]",
                    isMobile ? "h-9 w-9 rounded-[14px]" : "h-8 w-8",
                  )}
                >
                  <Info className="h-4 w-4" />
                </Button>
              </PopoverTrigger>

              <PopoverContent
                data-testid="paper-detail-info-popover"
                align="end"
                side="bottom"
                sideOffset={8}
                className="max-h-[calc(100svh-5.75rem)] w-[calc(100vw-1.5rem)] max-w-[22rem] overflow-y-auto overscroll-contain rounded-[20px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-3 shadow-[0_28px_60px_-38px_rgba(15,23,42,0.4)]"
              >
                <div className="space-y-3">
                  <div className="space-y-1 rounded-[16px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-3 py-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--px-shell-muted)]">
                      {t("community.detail.infoTitle")}
                    </p>
                    <p className="text-sm font-semibold leading-6 text-[color:var(--px-shell-ink)]">
                      {paper.title}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <InfoRow label={t("community.detail.infoAuthors")} value={authorsLabel} />
                    <InfoRow label={t("community.detail.infoPublished")} value={publishedLabel} />
                    <InfoRow label={t("community.detail.infoCategories")} value={categoryLabel} />
                    {paper.arxiv_id ? (
                      <InfoRow label={t("community.detail.infoArxivId")} value={paper.arxiv_id} />
                    ) : null}
                  </div>

                  <div className="space-y-2 rounded-[16px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-3 py-3">
                    {arxivUrl ? (
                      <div className="space-y-1">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--px-shell-muted)]">
                          {t("community.detail.infoArxiv")}
                        </p>
                        <a
                          href={arxivUrl}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="inline-flex text-sm font-medium text-[color:var(--px-shell-accent)] underline-offset-4 hover:underline"
                        >
                          {paper.arxiv_id}
                        </a>
                      </div>
                    ) : null}

                    {repositoryUrl ? (
                      <div className="space-y-1">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--px-shell-muted)]">
                          {t("community.detail.infoRepository")}
                        </p>
                        <a
                          href={repositoryUrl}
                          target="_blank"
                          rel="noreferrer noopener"
                          className="inline-flex break-all text-sm font-medium text-[color:var(--px-shell-accent)] underline-offset-4 hover:underline"
                        >
                          {repositoryUrl}
                        </a>
                      </div>
                    ) : null}
                  </div>
                </div>
              </PopoverContent>
            </Popover>

            <Button
              type="button"
              variant="ghost"
              size="icon"
              onClick={() => void handleShare()}
              aria-label={t("community.detail.shareAction")}
              title={t("community.detail.shareAction")}
              className={cn(
                "rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]",
                isMobile ? "h-9 w-9 rounded-[14px]" : "h-8 w-8",
              )}
            >
              <Share2 className="h-4 w-4" />
            </Button>

            {isMobile ? (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => setMobileToolbarCollapsed((current) => !current)}
                aria-label={
                  mobileToolbarCollapsed
                    ? t("community.detail.mobile.showToolbar", { defaultValue: "Show toolbar" })
                    : t("community.detail.mobile.hideToolbar", { defaultValue: "Hide toolbar" })
                }
                title={
                  mobileToolbarCollapsed
                    ? t("community.detail.mobile.showToolbar", { defaultValue: "Show toolbar" })
                    : t("community.detail.mobile.hideToolbar", { defaultValue: "Hide toolbar" })
                }
                className="h-9 w-9 rounded-[14px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]"
              >
                {mobileToolbarCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
              </Button>
            ) : null}
          </div>
        </div>

        {!isMobile || !mobileToolbarCollapsed ? (
          <div
            data-testid={isMobile ? "paper-detail-header-mobile-modes" : undefined}
            className={cn("flex justify-center px-1", isMobile ? "min-w-0" : "col-start-2 lg:pr-[20vw]")}
          >
            <SegmentedControl
              value={selectedMode}
              onValueChange={onSelectMode}
              items={modeItems}
              className="w-full max-w-[34rem] rounded-[12px] border border-[color:color-mix(in_srgb,var(--px-shell-line)_78%,white)] bg-transparent p-0.5 shadow-none"
              itemClassName={cn(
                "rounded-[8px] font-semibold normal-case tracking-normal",
                isMobile ? "min-h-10 px-2 text-[11px]" : "min-h-8 px-3 text-[12px] md:min-h-9 md:px-4",
              )}
            />
          </div>
        ) : null}
      </div>
    </nav>
  )
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[14px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-3 py-2.5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[color:var(--px-shell-muted)]">
        {label}
      </p>
      <p className="mt-1 text-sm leading-6 text-[color:var(--px-shell-ink)]">{value}</p>
    </div>
  )
}
