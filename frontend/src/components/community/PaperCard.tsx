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
    <Link
      to={`/paper/${paper.id}`}
      onMouseEnter={prefetchDetailNavigation}
      onFocus={prefetchDetailNavigation}
      onPointerDown={prefetchDetailNavigation}
      className="bg-surface-container-lowest rounded-xl p-5 border border-outline-variant/10 shadow-sm hover:shadow-md hover:border-primary/20 transition-all flex flex-col gap-3 group cursor-pointer text-left block"
    >
      <div className="flex items-center justify-between">
        <PaperStatusBadge kind="translation" value={paper.trans_status} />
        <span className="text-tertiary text-[10px] font-medium">
          {publishedAt ? new Date(publishedAt).toLocaleDateString() : t("community.card.dateUnknown")}
        </span>
      </div>

      <div>
        <h3 className="text-lg font-bold leading-tight group-hover:text-primary transition-colors text-on-surface">
          {paper.title}
        </h3>
        <p className="text-tertiary text-xs mt-1">{authorsLabel}</p>
      </div>

      <p className="text-on-surface-variant text-xs line-clamp-2 leading-relaxed">
        {abstractPreview}
      </p>

      <div className="flex flex-wrap gap-2">
        {paper.categories.slice(0, 3).map((cat) => (
          <span key={cat} className="text-[9px] font-bold text-tertiary bg-surface-container px-2 py-0.5 rounded uppercase">
            #{cat.toLowerCase()}
          </span>
        ))}
        {paper.categories.length === 0 && (
           <span className="text-[9px] font-bold text-tertiary bg-surface-container px-2 py-0.5 rounded uppercase">
             #uncategorized
           </span>
        )}
      </div>

      <div className="flex items-center justify-between pt-3 mt-auto border-t border-outline-variant/5">
        <div className="flex gap-4">
          <div className="flex items-center gap-1.5 text-tertiary group-hover:text-on-surface transition-colors">
            <span className="material-symbols-outlined text-base" style={{ fontVariationSettings: "'FILL' 0" }}>favorite</span>
            <span className="text-[11px] font-bold">0</span>
          </div>
          <div className="flex items-center gap-1.5 text-tertiary group-hover:text-on-surface transition-colors">
            <span className="material-symbols-outlined text-base">chat_bubble</span>
            <span className="text-[11px] font-bold">0</span>
          </div>
        </div>
        <div className="flex -space-x-2">
           <div className="w-6 h-6 rounded-full border-2 border-surface-container-lowest bg-surface-container-highest flex items-center justify-center overflow-hidden" title={paper.source === "arxiv" ? "Source: arXiv" : "Source: Upload"}>
             <span className="text-[8px] font-bold text-tertiary">{paper.source.charAt(0).toUpperCase()}</span>
           </div>
           {paper.latest_asset && (
             <div className="w-6 h-6 rounded-full border-2 border-surface-container-lowest bg-primary text-[8px] flex items-center justify-center font-bold text-on-primary" title={assetLabel}>
               <span className="material-symbols-outlined text-[10px]">description</span>
             </div>
           )}
        </div>
      </div>
    </Link>
  )
}
