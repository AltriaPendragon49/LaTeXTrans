import {
  ArrowLeft,
  Clock3,
  FileStack,
  Languages,
  Layers3,
  ScrollText,
} from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link, useParams } from "react-router-dom"

import { PaperActionShell } from "@/components/community/PaperActionShell"
import { PaperDetailSkeleton } from "@/components/community/PaperDetailSkeleton"
import { PaperMetaRow } from "@/components/community/PaperMetaRow"
import { PaperStatusBadge } from "@/components/community/PaperStatusBadge"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { usePaperDetail } from "@/hooks/use-paper-detail"
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

export default function PaperDetailPage() {
  const { t } = useTranslation()
  const { paperId } = useParams<{ paperId: string }>()
  const { paper, loading, error, notFound } = usePaperDetail(paperId)

  if (loading) {
    return (
      <div className="min-h-full bg-[#151515] px-4 py-6 text-slate-100 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <PaperDetailSkeleton />
        </div>
      </div>
    )
  }

  if (notFound || !paper) {
    return (
      <div className="min-h-full bg-[#151515] px-4 py-6 text-slate-100 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-4xl rounded-[32px] border border-white/10 bg-slate-950/70 px-6 py-14 text-center">
          <h1 className="text-3xl font-semibold text-white">{t("community.detail.notFoundTitle")}</h1>
          <p className="mt-3 text-sm text-slate-400">{t("community.detail.notFoundDescription")}</p>
          <Button asChild variant="outline" className="mt-6 rounded-2xl border-white/10 bg-white/[0.03] text-slate-100">
            <Link to="/">{t("community.detail.backToFeed")}</Link>
          </Button>
        </div>
      </div>
    )
  }

  const authorsLabel = formatAuthors(paper.authors, t("community.card.authorsUnavailable"))
  const abstractText =
    paper.abstract_translated || paper.abstract_raw || t("community.detail.abstractUnavailable")
  const assetLabel = paper.latest_asset
    ? `${getAssetTypeLabel(paper.latest_asset.asset_type, t)} · ${paper.latest_asset.file_name}`
    : t("community.card.assetUnavailable")

  return (
    <div className="min-h-full bg-[#151515] px-4 py-6 text-slate-100 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-5">
        <Button
          asChild
          variant="ghost"
          className="min-h-11 rounded-full border border-white/10 bg-white/[0.03] px-4 text-slate-100 hover:bg-white/[0.06]"
        >
          <Link to="/">
            <ArrowLeft className="h-4 w-4" />
            {t("community.detail.backToFeed")}
          </Link>
        </Button>

        <section className="rounded-[28px] border border-white/10 bg-[#1b1b1b] p-5 shadow-[0_22px_44px_-34px_rgba(0,0,0,0.86)] sm:p-7">
          <div className="flex flex-wrap gap-2">
            <PaperStatusBadge kind="community" value={paper.community_status} />
            <PaperStatusBadge kind="translation" value={paper.trans_status} />
            {paper.arxiv_id ? (
              <Badge className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-slate-200">
                {t("community.detail.arxivBadge", { value: paper.arxiv_id })}
              </Badge>
            ) : null}
          </div>

          <div className="mt-5 space-y-2.5">
            <h1 className="max-w-5xl text-balance text-[2.2rem] font-semibold tracking-tight text-white sm:text-[3rem]">
              {paper.title}
            </h1>
            <p className="max-w-3xl text-base text-slate-300">{authorsLabel}</p>
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
              {paper.categories.length
                ? paper.categories.join(" · ")
                : t("community.card.categoriesUnavailable")}
            </p>
          </div>

          <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-white/8 pt-4">
            <div className="rounded-full border border-white/8 bg-white/[0.03] px-3 py-2 text-xs text-slate-400">
              {paper.source === "arxiv"
                ? t("community.detail.sourceArxiv")
                : t("community.detail.sourceUpload")}
            </div>
            {paper.arxiv_id ? (
              <div className="rounded-full border border-white/8 bg-white/[0.03] px-3 py-2 text-xs text-slate-400">
                {t("community.detail.arxivBadge", { value: paper.arxiv_id })}
              </div>
            ) : null}
          </div>

          <div className="mt-8 grid gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,0.78fr)]">
            <div className="space-y-6">
              <Card className="rounded-[24px] border-white/10 bg-[#202020] text-slate-100 shadow-none">
                <CardHeader className="pb-4">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <ScrollText className="h-4 w-4 text-slate-300" />
                    {t("community.detail.abstractTitle")}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm leading-7 text-slate-300">
                  <p>{abstractText}</p>
                </CardContent>
              </Card>

              <Card className="rounded-[24px] border-white/10 bg-[#202020] text-slate-100 shadow-none">
                <CardHeader className="pb-4">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Languages className="h-4 w-4 text-slate-300" />
                    {t("community.detail.communitySelectionTitle")}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4 text-sm text-slate-300">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                        {t("community.detail.selectedTask")}
                      </p>
                      <p className="mt-2 break-all text-sm text-slate-100">
                        {paper.community_selected_task_id ?? t("community.detail.unavailable")}
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                        {t("community.detail.selectedAsset")}
                      </p>
                      <p className="mt-2 break-all text-sm text-slate-100">
                        {paper.community_selected_asset_id ?? t("community.detail.unavailable")}
                      </p>
                    </div>
                  </div>
                  <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">
                      {t("community.detail.latestAsset")}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-slate-100">{assetLabel}</p>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-6">
              <Card className="rounded-[24px] border-white/10 bg-[#202020] text-slate-100 shadow-none">
                <CardHeader className="pb-4">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Layers3 className="h-4 w-4 text-slate-300" />
                    {t("community.detail.metadataTitle")}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-5">
                  <PaperMetaRow
                    publishedAt={paper.official_published_at ?? paper.created_at}
                    views={paper.view_count}
                    likes={paper.like_count}
                    favorites={paper.favorite_count}
                    comments={paper.comment_count}
                    assetLabel={assetLabel}
                  />

                  <div className="grid gap-3">
                    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
                      <p className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-slate-500">
                        <Clock3 className="h-3.5 w-3.5" />
                        {t("community.detail.timelineTitle")}
                      </p>
                      <p className="mt-2 text-sm text-slate-100">
                        {paper.official_published_at
                          ? t("community.detail.officialPublishedAt", { value: paper.official_published_at })
                          : t("community.detail.createdAt", { value: paper.created_at ?? t("community.detail.unavailable") })}
                      </p>
                    </div>

                    <div className="rounded-2xl border border-white/8 bg-white/[0.03] p-4">
                      <p className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-slate-500">
                        <FileStack className="h-3.5 w-3.5" />
                        {t("community.detail.sourceTitle")}
                      </p>
                      <p className="mt-2 text-sm text-slate-100">
                        {paper.source === "arxiv"
                          ? t("community.detail.sourceArxiv")
                          : t("community.detail.sourceUpload")}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <PaperActionShell />

              {error ? (
                <p className="text-xs text-slate-500">{error}</p>
              ) : null}
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
