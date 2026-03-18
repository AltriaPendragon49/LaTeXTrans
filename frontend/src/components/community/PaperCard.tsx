import { ArrowUpRight } from "lucide-react"
import { useMemo } from "react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { CommunityPaper } from "@/types/community"

import { PaperMetaRow } from "./PaperMetaRow"
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
  const abstractPreview =
    paper.abstract_translated ||
    paper.abstract_raw ||
    t("community.card.abstractPlaceholder")

  const publishedAt = paper.official_published_at ?? paper.created_at

  return (
    <Card
      className={cn(
        "group relative overflow-hidden rounded-[24px] border bg-[#1b1b1b] text-slate-100 shadow-[0_24px_48px_-42px_rgba(0,0,0,0.85)] transition duration-200 hover:-translate-y-0.5 hover:border-white/16 hover:shadow-[0_28px_56px_-42px_rgba(0,0,0,0.88)]",
        paper.community_status === "official"
          ? "border-slate-300/14"
          : "border-white/10",
      )}
    >
      <div
        className={cn(
          "absolute inset-y-0 left-0 w-1",
          paper.community_status === "official" ? "bg-slate-300/55" : "bg-slate-500/28",
        )}
      />

      <div className="p-6">
        <div className="flex flex-wrap items-center gap-2">
          <PaperStatusBadge kind="community" value={paper.community_status} />
          <PaperStatusBadge kind="translation" value={paper.trans_status} />
          <div className="ml-auto rounded-full border border-white/8 bg-white/[0.03] px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-500">
            {paper.source === "arxiv"
              ? t("community.detail.sourceArxiv")
              : t("community.detail.sourceUpload")}
          </div>
        </div>

        <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1.54fr)_minmax(250px,0.7fr)]">
          <div className="space-y-3">
          <Link
            to={`/paper/${paper.id}`}
            className="inline-flex max-w-full items-start text-balance text-2xl font-semibold leading-tight tracking-tight text-white transition hover:text-slate-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400"
          >
            <span className="line-clamp-2">{paper.title}</span>
          </Link>

          <p className="text-sm leading-6 text-slate-300">{authorsLabel}</p>
          <p className="text-xs uppercase tracking-[0.18em] text-slate-500">{categoriesLabel}</p>
          <p className="line-clamp-4 max-w-4xl text-sm leading-7 text-slate-300">
            {abstractPreview}
          </p>
          </div>

          <div className="space-y-4 rounded-[20px] border border-white/8 bg-[#202020] p-4">
            <div>
              <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                {t("community.detail.communitySelectionTitle")}
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-200">{assetLabel}</p>
            </div>
            <div className="rounded-[16px] border border-white/8 bg-[#181818] px-3 py-3 text-xs text-slate-400">
              {paper.arxiv_id
                ? t("community.card.arxivId", { value: paper.arxiv_id })
                : t("community.card.uploadSource")}
            </div>
            <Button
              asChild
              variant="ghost"
              className="min-h-11 w-full rounded-[18px] border border-white/10 bg-white/[0.03] px-4 text-slate-100 hover:bg-white/[0.06] hover:text-white"
            >
              <Link to={`/paper/${paper.id}`}>
                {t("community.card.viewDetail")}
                <ArrowUpRight className="h-4 w-4 transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </Link>
            </Button>
          </div>
        </div>

        <div className="mt-6 border-t border-white/8 pt-5">
          <PaperMetaRow
            publishedAt={publishedAt}
            views={paper.view_count}
            likes={paper.like_count}
            favorites={paper.favorite_count}
            comments={paper.comment_count}
            assetLabel={assetLabel}
          />
        </div>

        <div className="mt-4 text-xs text-slate-500">
          {paper.arxiv_id
            ? t("community.card.arxivId", { value: paper.arxiv_id })
            : t("community.card.uploadSource")}
        </div>
      </div>
    </Card>
  )
}
