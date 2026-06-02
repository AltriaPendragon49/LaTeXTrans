import { AnimatePresence, motion } from "framer-motion"
import { Clock3, Eye, Flame, Heart, Search, X, type LucideIcon } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"

import { useAuth } from "@/contexts/AuthContext"
import { PaperCard } from "@/features/community-paper/components/PaperCard"
import { PaperCardSkeleton } from "@/features/community-paper/components/PaperCardSkeleton"
import { PaperFeedEmptyState } from "@/features/community-paper/components/PaperFeedEmptyState"
import { PaperFeedErrorState } from "@/features/community-paper/components/PaperFeedErrorState"
import { useCommunityPapers } from "@/features/community-paper/hooks/useCommunityPapers"
import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import { deleteCommunityPaper } from "@/lib/community-api"
import type { CommunityFeedSort, CommunityPaper } from "@/types/community"
import { Button } from "@/ui/button/Button"
import { HotWindowFilter } from "@/features/community-paper/components/HotWindowFilter"
import { FilterToolbar } from "@/ui/filter-toolbar/FilterToolbar"
import { Pill } from "@/ui/pill/Pill"

/** 排序选项 */
interface FeedSortOption {
  value: CommunityFeedSort
  label: string
  icon: LucideIcon
}

/**
 * 社区论文流主页面组件
 * 展示社区论文列表，支持四种排序方式（hot/latest/views/likes）、搜索关键词过滤、
 * 热榜时间窗口筛选、管理员删除和无限滚动加载。
 * 使用 SSR Bootstrap 数据优化首屏渲染速度
 */
export default function CommunityFeedSurface() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [searchInput, setSearchInput] = useState("")
  const [query, setQuery] = useState("")
  const [activeTab, setActiveTab] = useState<CommunityFeedSort>("hot")
  const [hotWindow, setHotWindow] = useState("30d")
  const [deletingPaperId, setDeletingPaperId] = useState<string | null>(null)
  const isAdmin = hasAdminRole(user?.roles)
  const inputRef = useRef<HTMLInputElement>(null)

  const { items, total, hasMore, loading, loadingMore, error, loadMore, refetch } =
    useCommunityPapers(activeTab, query, hotWindow)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const feedSortOptions: FeedSortOption[] = [
    {
      value: "hot",
      label: t("community.feed.sort.hot"),
      icon: Flame,
    },
    {
      value: "latest",
      label: t("community.feed.sort.latest"),
      icon: Clock3,
    },
    {
      value: "views",
      label: t("community.feed.sort.views"),
      icon: Eye,
    },
    {
      value: "likes",
      label: t("community.feed.sort.likes"),
      icon: Heart,
    },
  ]

  /** 提交搜索查询 */
  function handleSearchSubmit(nextValue: string) {
    const normalized = nextValue.trim()
    if (!normalized) {
      return
    }
    setQuery(normalized)
  }

  /** 管理员删除论文 */
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
      className="mx-auto flex w-full max-w-4xl flex-col gap-3 pt-2 text-[color:var(--px-shell-ink)]"
    >
      <div className="mb-4 mt-2 flex flex-col items-center px-4 text-center">
        <h1 className="mb-2 text-3xl font-black tracking-tight text-[color:var(--px-shell-ink)] sm:text-4xl">
          {t("community.feed.hero.titlePrefix")}
          <span className="text-[color:var(--px-shell-accent)]">
            {t("community.feed.hero.titleAccent")}
          </span>
        </h1>
        <p className="max-w-2xl text-xs leading-relaxed text-[color:var(--px-shell-muted)]/80 sm:text-sm">
          {t("community.feed.hero.description")}
        </p>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault()
          handleSearchSubmit(searchInput)
        }}
        className="flex w-full items-center gap-2 rounded-full border border-[color:var(--px-shell-line-strong)] bg-[color:var(--px-shell-panel-strong)] px-4 py-1.5 shadow-[0_20px_40px_-34px_rgba(8,23,38,0.22)] transition-all focus-within:border-[color:var(--px-shell-accent)] focus-within:ring-1 focus-within:ring-[color:var(--px-shell-accent)]"
      >
        <input
          ref={inputRef}
          autoFocus
          type="text"
          value={searchInput}
          onChange={(event) => setSearchInput(event.target.value)}
          placeholder={t("community.feed.searchPlaceholder")}
          aria-label={t("community.feed.searchAriaLabel")}
          className="min-w-0 flex-1 bg-transparent text-sm text-[color:var(--px-shell-ink)] outline-none placeholder:text-[color:var(--px-shell-muted)]/50"
        />

        {searchInput.length > 0 ? (
          <button
            type="button"
            onClick={() => {
              setSearchInput("")
              setQuery("")
              inputRef.current?.focus()
            }}
            className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[color:var(--px-shell-muted)] transition-colors hover:bg-[color:var(--px-shell-line)] hover:text-[color:var(--px-shell-ink)]"
            aria-label={t("community.feed.clearSearch")}
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : null}

        <button
          type="submit"
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[color:var(--px-shell-accent)] text-white transition-colors hover:bg-[color:var(--px-shell-accent-strong)]"
          aria-label={t("community.feed.searchLabel")}
        >
          <Search className="h-3.5 w-3.5" />
        </button>
      </form>

      <div className="mt-2 flex flex-col gap-1">
        <FilterToolbar
          options={feedSortOptions.map((option) => ({
            value: option.value,
            label: option.label,
            icon: <option.icon className="h-4 w-4" />,
          }))}
          value={activeTab}
          onValueChange={(nextValue) => setActiveTab(nextValue as CommunityFeedSort)}
          className="pb-1"
          actions={
            activeTab === "hot" ? (
              <HotWindowFilter
                selectedWindow={hotWindow}
                onWindowChange={setHotWindow}
              />
            ) : undefined
          }
          meta={
            query ? (
              <Pill className="px-3 py-2 text-xs font-medium normal-case tracking-normal">
                {t("community.feed.resultsFiltered", { count: total, query })}
              </Pill>
            ) : undefined
          }
        />

        {activeTab === "hot" ? (
          <div className="inline-flex max-w-full items-center gap-2 self-start rounded-full border border-[color:var(--px-shell-line-strong)] bg-[color:var(--px-shell-panel-strong)]/85 px-3 py-1.5 text-xs leading-relaxed text-[color:var(--px-shell-muted)] shadow-[0_14px_32px_-30px_rgba(8,23,38,0.28)] sm:text-sm">
            <Flame className="h-3.5 w-3.5 shrink-0 text-[color:var(--px-shell-accent)]" />
            <span className="min-w-0">{t("community.feed.hotExplanation")}</span>
          </div>
        ) : null}
      </div>

      <div className="relative">
        {error ? <PaperFeedErrorState onRetry={refetch} /> : null}

        <AnimatePresence mode="wait">
          {!error && loading ? (
            <motion.div
              key={`skeleton-${hotWindow}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="grid gap-3"
            >
              {Array.from({ length: 3 }).map((_, index) => (
                <div key={index} className="h-full">
                  <PaperCardSkeleton />
                </div>
              ))}
              <div className="flex justify-center py-8">
                <div className="flex items-center gap-3 text-[color:var(--px-shell-muted)]">
                  <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-[color:var(--px-shell-accent)]" />
                  <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-[color:var(--px-shell-accent)] [animation-delay:-0.15s]" />
                  <div className="h-1.5 w-1.5 animate-bounce rounded-full bg-[color:var(--px-shell-accent)] [animation-delay:-0.3s]" />
                  <span className="ml-2 text-[10px] font-black uppercase tracking-[0.3em]">
                    {t("common.status.loading")}
                  </span>
                </div>
              </div>
            </motion.div>
          ) : null}

          {!error && !loading && !items.length ? (
            <motion.div
              key={`empty-${hotWindow}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              <PaperFeedEmptyState />
            </motion.div>
          ) : null}

          {!error && !loading && items.length > 0 ? (
            <motion.div
              key={`items-${hotWindow}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
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
            </motion.div>
          ) : null}
        </AnimatePresence>
      </div>
    </section>
  )
}
