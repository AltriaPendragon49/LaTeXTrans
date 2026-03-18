import { CalendarDays, Eye, Files, Heart, MessageSquare, Star } from "lucide-react"
import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"

interface PaperMetaRowProps {
  publishedAt: string | null
  views?: number
  likes?: number
  favorites?: number
  comments?: number
  assetLabel?: string | null
  className?: string
}

export function PaperMetaRow({
  publishedAt,
  views = 0,
  likes = 0,
  favorites = 0,
  comments = 0,
  assetLabel,
  className,
}: PaperMetaRowProps) {
  const { i18n, t } = useTranslation()

  const formattedDate = publishedAt
    ? new Intl.DateTimeFormat(i18n.language, {
        year: "numeric",
        month: "short",
        day: "numeric",
      }).format(new Date(publishedAt))
    : t("community.card.dateUnknown")

  const items = [
    {
      key: "published",
      icon: CalendarDays,
      label: formattedDate,
      ariaLabel: t("community.card.publishedAt", { value: formattedDate }),
    },
    {
      key: "views",
      icon: Eye,
      label: String(views),
      ariaLabel: t("community.card.views", { count: views }),
    },
    {
      key: "likes",
      icon: Heart,
      label: String(likes),
      ariaLabel: t("community.card.likes", { count: likes }),
    },
    {
      key: "favorites",
      icon: Star,
      label: String(favorites),
      ariaLabel: t("community.card.favorites", { count: favorites }),
    },
    {
      key: "comments",
      icon: MessageSquare,
      label: String(comments),
      ariaLabel: t("community.card.comments", { count: comments }),
    },
  ]

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex flex-wrap items-center gap-2.5 text-xs text-slate-400">
        {items.map(({ key, icon: Icon, label, ariaLabel }) => (
          <div
            key={key}
            aria-label={ariaLabel}
            className="inline-flex min-h-10 items-center gap-1.5 rounded-full border border-white/8 bg-white/[0.03] px-3"
          >
            <Icon className="h-3.5 w-3.5 text-slate-500" />
            <span className="tabular-nums">{label}</span>
          </div>
        ))}
      </div>

      <div className="inline-flex min-h-10 max-w-full items-center gap-2 rounded-full border border-white/8 bg-white/[0.03] px-3 text-xs text-slate-300">
        <Files className="h-3.5 w-3.5 text-slate-500" />
        <span className="truncate">{assetLabel ?? t("community.card.assetUnavailable")}</span>
      </div>
    </div>
  )
}
