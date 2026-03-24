import { Search, Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import type { CommunityFeedSort } from "@/types/community"

const SORTS: CommunityFeedSort[] = ["latest", "translated", "hot"]

function getSortLabel(entry: CommunityFeedSort, t: (key: string) => string) {
  switch (entry) {
    case "latest":
      return t("community.feed.sort.latest")
    case "translated":
      return t("community.feed.sort.translated")
    case "hot":
      return t("community.feed.sort.hot")
  }
}

interface PaperFeedToolbarProps {
  sort: CommunityFeedSort
  onSortChange: (value: CommunityFeedSort) => void
  query: string
  onQueryChange: (value: string) => void
  showSearch?: boolean
}

export function PaperFeedToolbar({
  sort,
  onSortChange,
  query,
  onQueryChange,
  showSearch = true,
}: PaperFeedToolbarProps) {
  const { t } = useTranslation()

  return (
    <div className="rounded-[24px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-4 shadow-[var(--shell-panel-shadow)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="inline-flex flex-wrap gap-2 rounded-[18px] border border-[color:var(--shell-border)] bg-[var(--shell-surface-muted)] p-1">
          {SORTS.map((entry) => (
            <button
              key={entry}
              type="button"
              onClick={() => onSortChange(entry)}
              className={cn(
                "min-h-11 rounded-[14px] px-4 text-sm font-medium transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400",
                sort === entry
                  ? "bg-slate-500/14 text-[var(--shell-heading)] shadow-[inset_0_0_0_1px_var(--shell-border)]"
                  : "text-[var(--shell-text-soft)] hover:bg-[var(--shell-pill)] hover:text-[var(--shell-heading)]",
              )}
            >
              {getSortLabel(entry, t)}
            </button>
          ))}
        </div>

        {showSearch ? (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
            <div className="relative min-w-0 sm:w-[320px]">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--shell-text-muted)]" />
              <Input
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                placeholder={t("community.feed.searchPlaceholder")}
                aria-label={t("community.feed.searchAriaLabel")}
                className="h-11 rounded-[18px] border-[color:var(--shell-border)] bg-[var(--shell-surface-muted)] pl-9 text-[var(--shell-heading)] placeholder:text-[var(--shell-text-muted)]"
              />
            </div>

            <Button
              asChild
              className="h-11 rounded-[18px] bg-[var(--shell-accent)] px-5 text-[var(--shell-accent-foreground)] shadow-sm hover:bg-[var(--shell-accent-hover)]"
            >
              <Link to="/tools?panel=translate">
                <Sparkles className="h-4 w-4" />
                {t("community.nav.paperTools")}
              </Link>
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  )
}
