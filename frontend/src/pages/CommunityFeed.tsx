import { ArrowRight, LibraryBig, Sparkles, Telescope } from "lucide-react"
import { useMemo, useState } from "react"
import { useTranslation } from "react-i18next"

import { PaperCard } from "@/components/community/PaperCard"
import { PaperCardSkeleton } from "@/components/community/PaperCardSkeleton"
import { PaperFeedEmptyState } from "@/components/community/PaperFeedEmptyState"
import { PaperFeedErrorState } from "@/components/community/PaperFeedErrorState"
import { PaperFeedToolbar } from "@/components/community/PaperFeedToolbar"
import { useCommunityPapers } from "@/hooks/use-community-papers"
import type { CommunityFeedSort } from "@/types/community"

export default function CommunityFeedPage() {
  const { t } = useTranslation()
  const [sort, setSort] = useState<CommunityFeedSort>("latest")
  const [query, setQuery] = useState("")
  const { items, total, loading, error, refetch } = useCommunityPapers(sort, query)

  const summary = useMemo(
    () => [
      {
        key: "official",
        label: t("community.feed.summary.officialLabel"),
        value: items.filter((entry) => entry.community_status === "official").length,
      },
      {
        key: "translated",
        label: t("community.feed.summary.translatedLabel"),
        value: items.filter((entry) => entry.trans_status === "completed").length,
      },
      {
        key: "tracked",
        label: t("community.feed.summary.trackedLabel"),
        value: total,
      },
    ],
    [items, t, total],
  )

  return (
    <div className="min-h-full bg-[var(--shell-bg)] px-4 py-6 text-[var(--shell-text)] transition-colors sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-6xl flex-col gap-5">
        <section className="overflow-hidden rounded-[28px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] px-5 py-6 shadow-[var(--shell-panel-shadow)] sm:px-7">
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.62fr)_260px]">
            <div className="max-w-3xl space-y-4">
              <div className="space-y-3">
                <h1 className="max-w-4xl text-balance text-[clamp(2.1rem,4.6vw,3.6rem)] font-semibold tracking-[-0.04em] text-[var(--shell-heading)]">
                  {t("community.feed.title")}
                </h1>
                <p className="max-w-2xl text-[15px] leading-7 text-[var(--shell-text-soft)]">
                  {t("community.feed.description")}
                </p>
              </div>
              <div className="grid gap-3 border-t border-[color:var(--shell-border-strong)] pt-4 md:grid-cols-[minmax(0,170px)_minmax(0,1fr)]">
                <div className="rounded-[22px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] p-4">
                  <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-[var(--shell-text-muted)]">
                    <LibraryBig className="h-4 w-4 text-[var(--shell-icon)]" />
                    <span>{t("community.feed.summary.trackedLabel")}</span>
                  </div>
                  <p className="mt-3 text-3xl font-semibold tracking-tight text-[var(--shell-heading)]">{total}</p>
                </div>
                <div className="rounded-[22px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] p-4 text-sm text-[var(--shell-text-soft)]">
                  <div className="flex items-start gap-3">
                    <Telescope className="mt-0.5 h-4 w-4 shrink-0 text-[var(--shell-icon)]" />
                    <div>
                      <p className="text-xs uppercase tracking-[0.18em] text-[var(--shell-text-muted)]">
                        {t("community.feed.summary.officialLabel")}
                      </p>
                      <p className="mt-2 leading-6 text-[var(--shell-text-soft)]">{t("community.feed.officialPriorityHint")}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-3 rounded-[22px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-strong)] p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="text-xs uppercase tracking-[0.22em] text-[var(--shell-text-muted)]">
                  {t("community.feed.title")}
                </div>
                <div className="text-[11px] uppercase tracking-[0.18em] text-[var(--shell-text-muted)] opacity-80">
                  {t("community.feed.summary.officialLabel")}
                </div>
              </div>
              <div className="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
                {summary.map((entry) => (
                  <div
                    key={entry.key}
                    className="rounded-[18px] border border-[color:var(--shell-border-strong)] bg-[var(--shell-surface-muted)] px-4 py-3"
                  >
                    <p className="text-xs uppercase tracking-[0.18em] text-[var(--shell-text-muted)]">{entry.label}</p>
                    <p className="mt-2 text-xl font-semibold text-[var(--shell-heading)]">{entry.value}</p>
                  </div>
                ))}
              </div>
              <div className="rounded-[18px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-muted)] px-4 py-3 text-sm text-[var(--shell-text-soft)]">
                <div className="flex items-start gap-2">
                  <Sparkles className="mt-0.5 h-4 w-4 text-[var(--shell-icon)]" />
                  <div>
                    <p className="font-medium text-[var(--shell-heading)]">{t("community.feed.summary.officialLabel")}</p>
                    <p className="mt-1 text-[var(--shell-text-muted)]">{t("community.feed.officialPriorityHint")}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <PaperFeedToolbar
          sort={sort}
          onSortChange={setSort}
          query={query}
          onQueryChange={setQuery}
        />

        <section className="space-y-4">
          <div className="flex items-center justify-between gap-3 px-1">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-[var(--shell-text-muted)]">
                {t("community.feed.summary.trackedLabel")}
              </p>
              <h2 className="mt-1.5 text-lg font-semibold tracking-tight text-[var(--shell-heading)]">{total}</h2>
            </div>
            <div className="hidden items-center gap-2 rounded-full border border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-4 py-2 text-sm text-[var(--shell-text-muted)] md:inline-flex">
              <span>{t("community.feed.summary.officialLabel")}</span>
              <ArrowRight className="h-4 w-4 text-[var(--shell-text-muted)]" />
            </div>
          </div>
          {loading ? (
            <div data-testid="community-feed-loading" className="grid gap-4">
              {Array.from({ length: 3 }).map((_, index) => (
                <PaperCardSkeleton key={index} />
              ))}
            </div>
          ) : error ? (
            <PaperFeedErrorState onRetry={refetch} />
          ) : items.length === 0 ? (
            <PaperFeedEmptyState />
          ) : (
            <div className="grid gap-4">
              {items.map((paper) => (
                <PaperCard key={paper.id} paper={paper} />
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
