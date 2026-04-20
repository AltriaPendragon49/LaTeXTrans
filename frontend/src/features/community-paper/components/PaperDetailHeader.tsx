import { ArrowLeft, ChevronDown, ChevronUp, Download, Languages, Timer } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { Button } from "@/ui/button/Button"
import { Pill } from "@/ui/pill/Pill"
import { SegmentedControl } from "@/ui/segmented-control/SegmentedControl"
import type { CommunityPaper, CommunityPaperReaderMode } from "@/types/community"

interface PaperDetailHeaderProps {
  paper: CommunityPaper
  selectedMode: CommunityPaperReaderMode
  availableModes: CommunityPaperReaderMode[]
  isHeaderExpanded: boolean
  authorsLabel: string
  stageLabel: string
  actionError: string | null
  canTranslate: boolean
  canViewProgress: boolean
  canDownload: boolean
  onSelectMode: (mode: CommunityPaperReaderMode) => void
  onToggleExpanded: (expanded: boolean) => void
  onTranslate: () => void
  onViewProgress: () => void
  onDownload: () => void
}

export function PaperDetailHeader({
  paper,
  selectedMode,
  availableModes,
  isHeaderExpanded,
  authorsLabel,
  stageLabel,
  actionError,
  canTranslate,
  canViewProgress,
  canDownload,
  onSelectMode,
  onToggleExpanded,
  onTranslate,
  onViewProgress,
  onDownload,
}: PaperDetailHeaderProps) {
  const { t } = useTranslation()
  const legacyModeLabels = {
    translated: t("community.detail.mode.translated"),
    translatedHtml: t("community.detail.mode.translatedHtml"),
  }
  void legacyModeLabels
  const publishedLabel = paper.official_published_at
    ? t("community.detail.officialPublishedAt", {
        value: new Date(paper.official_published_at).toLocaleDateString(),
      })
    : paper.created_at
      ? t("community.detail.createdAt", {
          value: new Date(paper.created_at).toLocaleDateString(),
        })
      : t("community.card.dateUnknown")
  const detailStats = [
    t("community.card.views", { count: paper.view_count || 0 }),
    t("community.card.likes", { count: paper.like_count || 0 }),
    t("community.card.favorites", { count: paper.favorite_count || 0 }),
    t("community.card.comments", { count: paper.comment_count || 0 }),
  ]
  const actionStatusLabel = actionError ? t("community.detail.errorTitle") : stageLabel
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

  return (
    <nav className="sticky top-0 z-10 flex shrink-0 flex-col border-b border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)]/95 backdrop-blur-xl transition-all duration-300">
      <div className="relative flex min-h-16 items-center justify-between gap-4 px-4 py-3 md:px-6">
        <div className="flex min-w-0 flex-1 items-center gap-4">
          <Button
            asChild
            variant="outline"
            size="icon"
            className="h-10 w-10 shrink-0 bg-white/70 text-[color:var(--px-shell-muted)] hover:text-[color:var(--px-shell-ink)]"
          >
            <Link to="/" aria-label={t("community.detail.backToFeed")}>
              <ArrowLeft className="h-5 w-5" />
            </Link>
          </Button>
          <div className="min-w-0 space-y-1">
            <p className="text-[10px] font-black uppercase tracking-[0.24em] text-[color:var(--px-shell-muted)]">
              {t("community.detail.readerTitle")}
            </p>
            <h1 className="truncate text-lg font-black text-[color:var(--px-shell-ink)] md:text-[1.35rem]" title={paper.title}>
              {paper.title}
            </h1>
          </div>
        </div>

        <div className="absolute left-1/2 top-1/2 hidden w-full max-w-md -translate-x-1/2 -translate-y-1/2 xl:block">
          <SegmentedControl
            value={selectedMode}
            onValueChange={onSelectMode}
            items={modeItems}
            className="w-full"
            itemClassName="px-4"
          />
        </div>

        <div className="ml-4 flex shrink-0 items-center justify-end flex-none gap-3 xl:w-80">
          <div className="flex items-center gap-2">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[color:var(--px-shell-accent-soft)] text-[11px] font-black uppercase text-[color:var(--px-shell-accent)]">
              {paper.title.charAt(0)}
            </div>
            {!isHeaderExpanded ? (
              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={() => onToggleExpanded(true)}
                className="ml-1 h-8 w-8 text-[color:var(--px-shell-muted)] hover:text-[color:var(--px-shell-accent)]"
                title={t("community.detail.metadataTitle")}
              >
                <ChevronDown className="h-4 w-4" />
              </Button>
            ) : null}
          </div>
        </div>
      </div>

      {isHeaderExpanded ? (
        <div className="animate-in slide-in-from-top-1 duration-200">
          <div className="flex flex-col gap-4 border-t border-[color:var(--px-shell-line)] px-4 py-4 md:px-6">
            <div className="flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between">
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  {paper.categories.length > 0
                    ? paper.categories.slice(0, 4).map((category) => (
                        <Pill
                          key={category}
                          className="bg-white/70"
                        >
                          {category}
                        </Pill>
                      ))
                    : (
                        <Pill className="bg-white/70">
                          {t("community.card.categoriesUnavailable")}
                        </Pill>
                      )}
                </div>

                <div className="flex flex-wrap items-center gap-2 text-xs text-[color:var(--px-shell-muted)]">
                  <Pill className="px-3 py-1.5 text-[11px] normal-case tracking-normal font-semibold text-[color:var(--px-shell-ink)]">
                    {authorsLabel}
                  </Pill>
                  <Pill className="px-3 py-1.5 text-[11px] normal-case tracking-normal font-semibold">
                    {publishedLabel}
                  </Pill>
                  <Pill tone="accent" className="px-3 py-1.5 text-[11px] normal-case tracking-normal font-semibold">
                    {actionStatusLabel}
                  </Pill>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-2 xl:justify-end">
                {canTranslate && !canViewProgress ? (
                  <Button
                    type="button"
                    onClick={onTranslate}
                    size="sm"
                    className="bg-[color:var(--px-shell-accent)] text-white hover:bg-[color:var(--px-shell-accent-strong)]"
                  >
                    <Languages className="h-3.5 w-3.5" />
                    {t("community.actions.translate")}
                  </Button>
                ) : null}
                {canViewProgress ? (
                  <Button
                    type="button"
                    onClick={onViewProgress}
                    variant="secondary"
                    size="sm"
                    className="bg-white/75"
                  >
                    <Timer className="h-3.5 w-3.5" />
                    {t("community.actions.viewProgress")}
                  </Button>
                ) : null}
                <Button
                  type="button"
                  disabled={!canDownload}
                  onClick={onDownload}
                  variant="outline"
                  size="sm"
                >
                  <Download className="h-3.5 w-3.5" />
                  {t("community.actions.download")}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => onToggleExpanded(false)}
                  className="h-9 w-9 text-[color:var(--px-shell-muted)] hover:text-[color:var(--px-shell-accent)]"
                  title={t("community.detail.timelineTitle")}
                >
                  <ChevronUp className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 border-t border-[color:var(--px-shell-line)] pt-4">
              {detailStats.map((entry) => (
                <Pill
                  key={entry}
                  className="px-3 py-1.5 text-[11px] normal-case tracking-normal font-semibold"
                >
                  {entry}
                </Pill>
              ))}
            </div>
          </div>
        </div>
      ) : null}
    </nav>
  )
}
