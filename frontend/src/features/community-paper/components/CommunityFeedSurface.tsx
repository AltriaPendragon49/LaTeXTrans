import { Clock3, Compass, Flame, Search, Trash2 } from "lucide-react"
import { useState, type ReactElement } from "react"
import { useTranslation } from "react-i18next"

import { PaperCard } from "@/features/community-paper/components/PaperCard"
import { PaperCardSkeleton } from "@/features/community-paper/components/PaperCardSkeleton"
import { PaperFeedEmptyState } from "@/features/community-paper/components/PaperFeedEmptyState"
import { PaperFeedErrorState } from "@/features/community-paper/components/PaperFeedErrorState"
import { useAuth } from "@/contexts/AuthContext"
import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import { useCommunityPapers } from "@/features/community-paper/hooks/useCommunityPapers"
import { deleteCommunityPaper } from "@/lib/community-api"
import type { CommunityFeedSort, CommunityPaper } from "@/types/community"
import { Button } from "@/ui/button/Button"
import { FilterToolbar } from "@/ui/filter-toolbar/FilterToolbar"
import { Pill } from "@/ui/pill/Pill"
import { SearchBar } from "@/ui/search-bar/SearchBar"

export default function CommunityFeedSurface() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [searchInput, setSearchInput] = useState("")
  const [query, setQuery] = useState("")
  const [activeTab, setActiveTab] = useState<CommunityFeedSort>("latest")
  const [deletingPaperId, setDeletingPaperId] = useState<string | null>(null)
  const isAdmin = hasAdminRole(user?.roles)

  const { items, total, hasMore, loading, loadingMore, error, loadMore, refetch } = useCommunityPapers(activeTab, query)
  const feedSortOptions = [
    {
      value: "hot",
      label: t("community.feed.sort.hot"),
      icon: <Flame className="h-4 w-4" />,
    },
    {
      value: "latest",
      label: t("community.feed.sort.latest"),
      icon: <Clock3 className="h-4 w-4" />,
    },
  ] satisfies Array<{
    value: CommunityFeedSort
    label: string
    icon: ReactElement
  }>

  function handleSearchSubmit(nextValue: string) {
    if (!nextValue.trim()) {
      return
    }
    setQuery(nextValue.trim())
  }

  async function handleDelete(paper: CommunityPaper) {
    const confirmed = window.confirm(
      t("community.admin.deleteConfirm", {
        title: paper.title,
      }),
    )

    if (!confirmed) {
      return
    }

    try {
      setDeletingPaperId(paper.id)
      await deleteCommunityPaper(paper.id)
      refetch()
    } finally {
      setDeletingPaperId(null)
    }
  }

  return (
    <section
      aria-label={t("community.feed.title")}
      className="mx-auto flex w-full max-w-4xl flex-col gap-3 text-[color:var(--px-shell-ink)]"
    >
      <SearchBar
        variant="inline"
        value={searchInput}
        onValueChange={setSearchInput}
        onSubmit={handleSearchSubmit}
        ariaLabel={t("community.feed.searchAriaLabel")}
        placeholder={t("community.feed.searchPlaceholder")}
        actionLabel={t("community.feed.searchLabel")}
        actionIcon={<Search className="h-4 w-4" />}
        className="w-full border-[color:var(--px-shell-line-strong)] bg-[color:var(--px-shell-panel-strong)] shadow-[0_20px_40px_-34px_rgba(8,23,38,0.22)]"
        meta={isAdmin ? (
          <Pill className="px-3 py-2 text-xs font-semibold normal-case tracking-normal">
            <Trash2 className="h-4 w-4" />
            {t("community.feed.adminHint")}
          </Pill>
        ) : undefined}
      />

      <FilterToolbar
        options={feedSortOptions}
        value={activeTab}
        onValueChange={(nextValue) => setActiveTab(nextValue as CommunityFeedSort)}
        className="pb-2"
        meta={
          <Pill className="px-3 py-2 text-xs font-medium normal-case tracking-normal">
            <Compass className="h-4 w-4" />
            {query
              ? t("community.feed.resultsFiltered", { count: total, query })
              : t("community.feed.resultsTotal", { count: total })}
          </Pill>
        }
      />

      <div className="relative">
          {error ? <PaperFeedErrorState onRetry={refetch} /> : null}

          {!error && loading ? (
            <div className="grid gap-3">
              {Array.from({ length: 3 }).map((_, index) => (
                <div key={index} className="h-full">
                  <PaperCardSkeleton />
                </div>
              ))}
              <div className="flex justify-center py-8">
                <div className="flex items-center gap-3 text-[color:var(--px-shell-muted)]">
                  <div className="w-1.5 h-1.5 rounded-full bg-[color:var(--px-shell-accent)] animate-bounce"></div>
                  <div className="w-1.5 h-1.5 rounded-full bg-[color:var(--px-shell-accent)] animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-1.5 h-1.5 rounded-full bg-[color:var(--px-shell-accent)] animate-bounce [animation-delay:-0.3s]"></div>
                  <span className="ml-2 text-[10px] font-black uppercase tracking-[0.3em]">
                    {t("common.status.loading")}
                  </span>
                </div>
              </div>
            </div>
          ) : null}

          {!error && !loading && !items.length ? <PaperFeedEmptyState /> : null}

          {!error && !loading && items.length > 0 ? (
            <>
              <div className="grid gap-3">
                {items.map((paper) => (
                  <PaperCard
                    key={paper.id}
                    paper={paper}
                    onDelete={isAdmin ? handleDelete : undefined}
                    deleting={deletingPaperId === paper.id}
                  />
                ))}
              </div>
              {hasMore ? (
                <div className="flex justify-center pt-4">
                  <Button
                    type="button"
                    onClick={() => void loadMore()}
                    disabled={loadingMore}
                    variant="outline"
                  >
                    {loadingMore ? `${t("common.actions.loadMore")}...` : t("common.actions.loadMore")}
                  </Button>
                </div>
              ) : null}
            </>
          ) : null}
      </div>
    </section>
  )
}
