import { Clock3, Flame, Search, Trash2, X } from "lucide-react"
import { useState, useEffect, useRef, type ReactElement } from "react"
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

export default function CommunityFeedSurface() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [searchInput, setSearchInput] = useState("")
  const [query, setQuery] = useState("")
  const [activeTab, setActiveTab] = useState<CommunityFeedSort>("latest")
  const [deletingPaperId, setDeletingPaperId] = useState<string | null>(null)
  const isAdmin = hasAdminRole(user?.roles)

  const inputRef = useRef<HTMLInputElement>(null)

  const { items, total, hasMore, loading, loadingMore, error, loadMore, refetch } = useCommunityPapers(activeTab, query)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

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
      // 1. 容器宽度缩小为 4xl，顶部留白压缩为 pt-2
      className="mx-auto flex w-full max-w-4xl flex-col gap-3 text-[color:var(--px-shell-ink)] pt-2"
    >

      {/* 2. 上下留白大幅压缩 (mb-4 mt-2) */}
      <div className="flex flex-col items-center text-center mb-4 mt-2 px-4">
        {/* 3. 主标题字号缩小 (text-2xl sm:text-3xl)，主标题和副标题之间的间距缩小 (mb-2) */}
        <h1 className="mb-2 text-2xl font-semibold tracking-tight sm:text-3xl text-[color:var(--px-shell-ink)]">
          探索、学习与<span className="text-[color:var(--px-shell-accent)] font-medium">创新</span>
        </h1>
        {/* 4. 副标题字号缩小 (text-xs sm:text-sm) */}
        <p className="text-xs sm:text-sm text-[color:var(--px-shell-muted)]/80 max-w-lg leading-relaxed font-light">
          我们精选论文并提供译文与解析，也提供翻译工具，助力论文研究与学习。
        </p>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault()
          handleSearchSubmit(searchInput)
        }}
        // 5. 搜索框上下内边距压缩 (py-1.5)
        className="flex w-full items-center gap-2 rounded-full border border-[color:var(--px-shell-line-strong)] bg-[color:var(--px-shell-panel-strong)] px-4 py-1.5 shadow-[0_20px_40px_-34px_rgba(8,23,38,0.22)] focus-within:border-[color:var(--px-shell-accent)] focus-within:ring-1 focus-within:ring-[color:var(--px-shell-accent)] transition-all"
      >
        {isAdmin ? (
          <Pill className="shrink-0 px-3 py-1 text-[10px] font-semibold normal-case tracking-normal">
            <Trash2 className="h-3 w-3" />
            {t("community.feed.adminHint")}
          </Pill>
        ) : null}

        <input
          ref={inputRef}
          autoFocus
          type="text"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder={t("community.feed.searchPlaceholder")}
          aria-label={t("community.feed.searchAriaLabel")}
          className="min-w-0 flex-1 bg-transparent text-sm text-[color:var(--px-shell-ink)] outline-none placeholder:text-[color:var(--px-shell-muted)]/50"
        />

        {searchInput.length > 0 && (
          <button
            type="button"
            onClick={() => {
              setSearchInput("")
              setQuery("")
              inputRef.current?.focus()
            }}
            // 清除按钮略微缩小
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[color:var(--px-shell-muted)] transition-colors hover:bg-[color:var(--px-shell-line)] hover:text-[color:var(--px-shell-ink)]"
            aria-label="Clear search"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}

        <button
          type="submit"
          // 搜索按钮略微缩小
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[color:var(--px-shell-accent)] text-white transition-colors hover:bg-[color:var(--px-shell-accent-strong)]"
          aria-label={t("community.feed.searchLabel")}
        >
          <Search className="h-3.5 w-3.5" />
        </button>
      </form>

      <FilterToolbar
        options={feedSortOptions}
        value={activeTab}
        onValueChange={(nextValue) => setActiveTab(nextValue as CommunityFeedSort)}
        className="pb-2 mt-2"
        meta={query ? (
          <Pill className="px-3 py-2 text-xs font-medium normal-case tracking-normal">
            {t("community.feed.resultsFiltered", { count: total, query })}
          </Pill>
        ) : undefined}
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