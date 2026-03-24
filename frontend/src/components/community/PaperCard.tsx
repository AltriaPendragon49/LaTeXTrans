import { ArrowUpRight } from "lucide-react"
import { useMemo } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { preloadPaperDetailRoute, prefetchCommunityPaperDetail } from "@/lib/community-api"
import { preloadPaperPreviewEnhancer } from "@/lib/paper-preview-enhancer"
import type { CommunityPaper } from "@/types/community"

import { PaperStatusBadge } from "./PaperStatusBadge"

interface PaperCardProps {
  paper: CommunityPaper
}

function getAssetTypeLabel(
  assetType: NonNullable<CommunityPaper["latest_asset"]>["asset_type"],
  t: (key: string) => string,
) {
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

export function PaperCard({ paper }: PaperCardProps) {
  const { t } = useTranslation()

  function prefetchDetailNavigation() {
    void preloadPaperDetailRoute()
    void prefetchCommunityPaperDetail(paper.id)
    void preloadPaperPreviewEnhancer()
  }

  const authorsLabel = useMemo(
    () => formatAuthors(paper.authors, t("community.card.authorsUnavailable")),
    [paper.authors, t],
  )

  const categoriesLabel = paper.categories.length
    ? paper.categories.slice(0, 3).join(" · ")
    : t("community.card.categoriesUnavailable")

  const assetLabel = paper.latest_asset
    ? `${getAssetTypeLabel(paper.latest_asset.asset_type, t)} · ${paper.latest_asset.file_name}`
    : t("community.card.assetUnavailable")

  const abstractPreview = paper.abstract_translated || paper.abstract_raw || t("community.card.abstractPlaceholder")

  const publishedAt = paper.official_published_at ?? paper.created_at

  return (
    <Card className="group overflow-hidden rounded-[26px] border border-[color:var(--shell-border)] bg-[color:color-mix(in_srgb,var(--shell-surface)_96%,transparent)] text-[var(--shell-text)] shadow-[var(--shell-panel-shadow)] transition duration-200 hover:-translate-y-0.5 hover:shadow-[var(--shell-panel-shadow-strong)]">
      <div className="p-6">
        <div className="flex flex-wrap items-center gap-2">
          <PaperStatusBadge kind="translation" value={paper.trans_status} />
          <div className="rounded-full border border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-[var(--shell-text-muted)]">
            {paper.source === "arxiv" ? t("community.detail.sourceArxiv") : t("community.detail.sourceUpload")}
          </div>
        </div>

        <div className="mt-5 space-y-4">
          <Link
            to={`/paper/${paper.id}`}
            onMouseEnter={prefetchDetailNavigation}
            onFocus={prefetchDetailNavigation}
            onPointerDown={prefetchDetailNavigation}
            className="block space-y-3"
          >
            <h2 className="text-balance text-[1.18rem] font-semibold leading-8 tracking-[-0.03em] text-[var(--shell-heading)] transition group-hover:text-white">
              {paper.title}
            </h2>

            <div className="text-sm text-[var(--shell-text-soft)]">{authorsLabel}</div>

            <div className="flex flex-wrap gap-2 text-xs text-[var(--shell-text-muted)]">
              <span className="rounded-full border border-[color:var(--shell-border)] bg-[var(--shell-surface-muted)] px-3 py-1">
                {categoriesLabel}
              </span>
            </div>

            <p className="line-clamp-4 text-[14px] leading-7 text-[var(--shell-text-soft)]">{abstractPreview}</p>
          </Link>

          <div className="grid gap-2 rounded-[20px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-muted)] px-4 py-3 text-sm text-[var(--shell-text-soft)]">
            <div>
              {publishedAt
                ? t("community.card.publishedAt", {
                    value: new Date(publishedAt).toLocaleDateString(),
                  })
                : t("community.card.dateUnknown")}
            </div>
            <div>{assetLabel}</div>
            <div>
              {paper.arxiv_id ? t("community.card.arxivId", { value: paper.arxiv_id }) : t("community.card.uploadSource")}
            </div>
          </div>

          <Button
            asChild
            className="h-11 rounded-full bg-[var(--shell-accent)] px-5 text-[var(--shell-accent-foreground)] hover:bg-[var(--shell-accent-hover)]"
          >
            <Link
              to={`/paper/${paper.id}`}
              onMouseEnter={prefetchDetailNavigation}
              onFocus={prefetchDetailNavigation}
              onPointerDown={prefetchDetailNavigation}
            >
              {t("community.card.viewDetail")}
              <ArrowUpRight className="h-4 w-4 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </Link>
          </Button>
        </div>
      </div>
    </Card>
  )
}
