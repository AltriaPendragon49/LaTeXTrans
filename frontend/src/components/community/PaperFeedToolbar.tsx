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
}

export function PaperFeedToolbar({
  sort,
  onSortChange,
  query,
  onQueryChange,
}: PaperFeedToolbarProps) {
  const { t } = useTranslation()

  return (
    <div className="rounded-[24px] border border-white/10 bg-[#1b1b1b] p-4 shadow-[0_18px_40px_-34px_rgba(0,0,0,0.78)]">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div className="inline-flex flex-wrap gap-2 rounded-[18px] border border-white/10 bg-[#222222] p-1">
          {SORTS.map((entry) => (
            <button
              key={entry}
              type="button"
              onClick={() => onSortChange(entry)}
              className={cn(
                "min-h-11 rounded-[14px] px-4 text-sm font-medium transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400",
                sort === entry
                  ? "bg-slate-500/14 text-slate-50 shadow-[inset_0_0_0_1px_rgba(148,163,184,0.22)]"
                  : "text-slate-300 hover:bg-white/[0.04] hover:text-white",
              )}
            >
              {getSortLabel(entry, t)}
            </button>
          ))}
        </div>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative min-w-0 sm:w-[320px]">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <Input
              value={query}
              onChange={(event) => onQueryChange(event.target.value)}
              placeholder={t("community.feed.searchPlaceholder")}
              aria-label={t("community.feed.searchAriaLabel")}
              className="h-11 rounded-[18px] border-white/10 bg-[#222222] pl-9 text-slate-100 placeholder:text-slate-500"
            />
          </div>

          <Button
            asChild
            className="h-11 rounded-[18px] bg-[#607487] px-5 text-white shadow-[0_16px_36px_-24px_rgba(0,0,0,0.75)] hover:bg-[#6c8195]"
          >
            <Link to="/translate">
              <Sparkles className="h-4 w-4" />
              {t("community.nav.newTranslation")}
            </Link>
          </Button>
        </div>
      </div>
    </div>
  )
}
