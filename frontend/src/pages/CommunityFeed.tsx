import { Search, Trash2 } from "lucide-react"
import { useState, type FormEvent } from "react"
import { useTranslation } from "react-i18next"

import { PaperCard } from "@/components/community/PaperCard"
import { PaperCardSkeleton } from "@/components/community/PaperCardSkeleton"
import { PaperFeedEmptyState } from "@/components/community/PaperFeedEmptyState"
import { PaperFeedErrorState } from "@/components/community/PaperFeedErrorState"
import { useAuth } from "@/contexts/AuthContext"
import { useCommunityPapers } from "@/hooks/use-community-papers"
import { deleteCommunityPaper } from "@/lib/community-api"
import type { CommunityFeedSort, CommunityPaper } from "@/types/community"

function hasAdminRole(roles: string[] | undefined) {
  return (roles ?? []).includes("admin")
}

export default function CommunityFeedPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const [searchInput, setSearchInput] = useState("")
  const [query, setQuery] = useState("")
  const [activeTab, setActiveTab] = useState<CommunityFeedSort>("latest")
  const [deletingPaperId, setDeletingPaperId] = useState<string | null>(null)
  const isAdmin = hasAdminRole(user?.roles)

  const { items, loading, error, refetch } = useCommunityPapers(activeTab, query)

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setQuery(searchInput.trim())
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
    <div className="flex-1 w-full bg-surface text-on-surface">
      <div className="max-w-6xl mx-auto px-8 py-8">
        <section className="mb-10">
          <div className="bg-surface-container-lowest rounded-2xl p-6 border border-outline-variant/20 shadow-sm">
            <form onSubmit={handleSubmit} className="relative">
              <textarea
                aria-label={t("community.feed.searchAriaLabel")}
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault()
                    if (searchInput.trim() !== "") {
                      setQuery(searchInput.trim())
                    }
                  }
                }}
                className="w-full bg-surface-container-low border-none rounded-xl p-5 text-on-surface-variant focus:ring-2 focus:ring-primary/10 min-h-[120px] resize-none text-lg font-light tracking-tight placeholder:text-slate-400"
                placeholder={t("community.feed.searchPlaceholder")}
              />

              <div className="absolute bottom-4 right-4 flex gap-3">
                {isAdmin ? (
                  <div className="px-4 py-2.5 rounded-full font-semibold text-sm border bg-slate-100 text-slate-600 dark:bg-surface-container-highest dark:text-on-surface-variant border-transparent inline-flex items-center gap-2">
                    <Trash2 className="w-4 h-4" />
                    {t("community.feed.adminHint")}
                  </div>
                ) : null}

                <button
                  type="submit"
                  aria-label={t("community.feed.searchLabel")}
                  className="px-8 py-2.5 bg-primary text-on-primary rounded-full font-semibold text-sm flex items-center gap-2 transition-all hover:opacity-90 shadow-lg shadow-primary/20"
                >
                  <Search className="text-lg w-4 h-4" />
                  {t("community.feed.searchLabel")}
                </button>
              </div>
            </form>
          </div>
        </section>

        <div className="flex justify-between items-center mb-8 border-b border-outline-variant/10">
          <div className="flex items-center gap-10">
            <button
              onClick={() => setActiveTab("hot")}
              className={`font-bold pb-4 flex items-center gap-2 transition-colors ${activeTab === "hot" ? "text-primary border-b-2 border-primary" : "text-tertiary hover:text-primary"}`}
            >
              <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>local_fire_department</span>
              {t("community.feed.sort.hot")}
            </button>
            <button
              onClick={() => setActiveTab("latest")}
              className={`font-bold pb-4 flex items-center gap-2 transition-colors ${activeTab === "latest" ? "text-primary border-b-2 border-primary" : "text-tertiary hover:text-primary"}`}
            >
              <span className="material-symbols-outlined text-sm">schedule</span>
              {t("community.feed.sort.latest")}
            </button>
            <button
              onClick={() => setActiveTab("translated")}
              className={`font-bold pb-4 flex items-center gap-2 transition-colors ${activeTab === "translated" ? "text-primary border-b-2 border-primary" : "text-tertiary hover:text-primary"}`}
            >
              <span className="material-symbols-outlined text-sm">translate</span>
              {t("community.feed.sort.translated")}
            </button>
          </div>

          <div className="flex gap-4 pb-4">
            <span className="flex items-center gap-2 px-4 py-1.5 text-tertiary text-sm font-medium">
              <span className="material-symbols-outlined text-xl">travel_explore</span>
              {query ? t("community.feed.resultsFiltered", { count: items.length, query }) : t("community.feed.resultsTotal", { count: items.length })}
            </span>
          </div>
        </div>

        <div className="flex flex-col gap-6 relative">
          {error ? <PaperFeedErrorState onRetry={refetch} /> : null}

          {!error && loading ? (
            <div className="flex flex-col gap-6">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="h-48">
                  <PaperCardSkeleton />
                </div>
              ))}
              <div className="flex justify-center py-8">
                <div className="flex items-center gap-3 text-tertiary">
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce"></div>
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-1.5 h-1.5 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]"></div>
                  <span className="text-[10px] font-black uppercase tracking-[0.3em] ml-2">Exploring more papers</span>
                </div>
              </div>
            </div>
          ) : null}

          {!error && !loading && !items.length ? <PaperFeedEmptyState /> : null}

          {!error && !loading && items.length > 0 ? (
            <>
              {items.map((paper) => (
                <PaperCard
                  key={paper.id}
                  paper={paper}
                  onDelete={isAdmin ? handleDelete : undefined}
                  deleting={deletingPaperId === paper.id}
                />
              ))}
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
