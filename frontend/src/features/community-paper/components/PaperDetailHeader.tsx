import { useEffect, useRef, useState } from "react"
import { ArrowLeft, Bookmark, Download, Info, Share2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link, useLocation } from "react-router-dom"

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
  onSelectMode: (mode: CommunityPaperReaderMode) => void
  onDownload: () => void
}

export function PaperDetailHeader({
  paper,
  selectedMode,
  availableModes,
  authorsLabel,
  canDownload,
  onSelectMode,
  onDownload,
}: PaperDetailHeaderProps) {
  const { t } = useTranslation()
  const location = useLocation()
  const shareTimerRef = useRef<number | null>(null)
  const [shareStatus, setShareStatus] = useState<"idle" | "copied">("idle")

  useEffect(() => {
    return () => {
      if (shareTimerRef.current !== null) {
        window.clearTimeout(shareTimerRef.current)
      }
    }
  }, [])

  const publishedLabel = paper.official_published_at
    ? t("community.detail.officialPublishedAt", {
        value: new Date(paper.official_published_at).toLocaleDateString(),
      })
    : paper.created_at
      ? t("community.detail.createdAt", {
          value: new Date(paper.created_at).toLocaleDateString(),
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

    await navigator.clipboard.writeText(shareUrl)
    setShareStatus("copied")
    if (shareTimerRef.current !== null) {
      window.clearTimeout(shareTimerRef.current)
    }
    shareTimerRef.current = window.setTimeout(() => {
      setShareStatus("idle")
      shareTimerRef.current = null
    }, 1800)
  }

  return (
    <nav className="sticky top-0 z-10 shrink-0 border-b border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)]/88 backdrop-blur-xl">
      <div className="grid min-h-12 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 px-2 py-1.5 md:px-3">
        <div className="flex items-center justify-start">
          <Button
            asChild
            variant="ghost"
            size="icon"
            className="h-8 w-8 rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]"
          >
            <Link to="/" aria-label={t("community.detail.backToFeed")} title={t("community.detail.backToFeed")}>
              <ArrowLeft className="h-4 w-4" />
            </Link>
          </Button>
        </div>

        <div className="flex justify-center px-1 lg:pr-[20vw]">
          <SegmentedControl
            value={selectedMode}
            onValueChange={onSelectMode}
            items={modeItems}
            className="w-full max-w-[34rem] rounded-[12px] border border-[color:color-mix(in_srgb,var(--px-shell-line)_78%,white)] bg-transparent p-0.5 shadow-none"
            itemClassName="min-h-8 rounded-[8px] px-3 text-[12px] font-semibold normal-case tracking-normal md:min-h-9 md:px-4"
          />
        </div>

        <div className="flex items-center justify-end gap-1">
          <span
            aria-live="polite"
            className={`mr-1 text-[11px] font-medium text-[color:var(--px-shell-accent)] transition-opacity duration-200 ${
              shareStatus === "copied" ? "opacity-100" : "opacity-0"
            }`}
          >
            {shareStatus === "copied" ? t("community.detail.shareCopied") : " "}
          </span>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={t("community.detail.favoriteAction")}
            title={t("community.detail.favoriteAction")}
            className="h-8 w-8 rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]"
          >
            <Bookmark className="h-4 w-4" />
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="icon"
            disabled={!canDownload}
            onClick={onDownload}
            aria-label={t("community.card.action.downloadTranslatedPdf")}
            title={t("community.card.action.downloadTranslatedPdf")}
            className="h-8 w-8 rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]"
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
                className="h-8 w-8 rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]"
              >
                <Info className="h-4 w-4" />
              </Button>
            </PopoverTrigger>

            <PopoverContent
              align="end"
              side="bottom"
              sideOffset={8}
              className="w-[22rem] rounded-[20px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-3 shadow-[0_28px_60px_-38px_rgba(15,23,42,0.4)]"
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
            className="h-8 w-8 rounded-[10px] border border-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]"
          >
            <Share2 className="h-4 w-4" />
          </Button>
        </div>
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
