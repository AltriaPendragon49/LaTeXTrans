import {
  AlertTriangle,
  CheckCircle2,
  CircleDashed,
  Clock3,
  RadioTower,
  ShieldCheck,
  Users,
} from "lucide-react"
import { useTranslation } from "react-i18next"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import type { CommunityStatus, TranslationStatus } from "@/types/community"

interface PaperStatusBadgeProps {
  kind: "community" | "translation"
  value: CommunityStatus | TranslationStatus
}

function getCommunityLabel(value: CommunityStatus, t: (key: string) => string) {
  switch (value) {
    case "official":
      return t("community.status.community.official")
    case "user_fallback":
      return t("community.status.community.user_fallback")
  }
}

function getTranslationLabel(value: TranslationStatus, t: (key: string) => string) {
  switch (value) {
    case "not_started":
      return t("community.status.translation.not_started")
    case "queued":
      return t("community.status.translation.queued")
    case "processing":
      return t("community.status.translation.processing")
    case "completed":
      return t("community.status.translation.completed")
    case "failed":
      return t("community.status.translation.failed")
  }
}

export function PaperStatusBadge({ kind, value }: PaperStatusBadgeProps) {
  const { t } = useTranslation()

  if (kind === "community") {
    const isOfficial = value === "official"
    return (
        <Badge
          className={cn(
            "gap-1 rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.18em]",
            isOfficial
            ? "border-slate-300/70 bg-slate-100 text-slate-700 dark:border-slate-300/35 dark:bg-slate-400/12 dark:text-slate-100"
            : "border-slate-300/70 bg-slate-100 text-slate-600 dark:border-slate-400/30 dark:bg-slate-500/10 dark:text-slate-200",
          )}
      >
        {isOfficial ? <ShieldCheck className="h-3.5 w-3.5" /> : <Users className="h-3.5 w-3.5" />}
        <span>{getCommunityLabel(value as CommunityStatus, t)}</span>
      </Badge>
    )
  }

  const config: Record<
    TranslationStatus,
    { icon: typeof CircleDashed; className: string }
  > = {
    not_started: {
      icon: CircleDashed,
      className: "border-slate-300/70 bg-slate-100 text-slate-700 dark:border-slate-500/30 dark:bg-slate-500/10 dark:text-slate-200",
    },
    queued: {
      icon: Clock3,
      className: "border-stone-300/70 bg-stone-100 text-stone-700 dark:border-stone-300/35 dark:bg-stone-400/10 dark:text-stone-100",
    },
    processing: {
      icon: RadioTower,
      className: "border-zinc-300/70 bg-zinc-100 text-zinc-700 dark:border-zinc-300/35 dark:bg-zinc-400/10 dark:text-zinc-100",
    },
    completed: {
      icon: CheckCircle2,
      className: "border-emerald-300/70 bg-emerald-50 text-emerald-700 dark:border-emerald-300/30 dark:bg-emerald-400/10 dark:text-emerald-100",
    },
    failed: {
      icon: AlertTriangle,
      className: "border-rose-300/70 bg-rose-50 text-rose-700 dark:border-rose-300/30 dark:bg-rose-400/10 dark:text-rose-100",
    },
  }

  const selected = config[value as TranslationStatus]
  const Icon = selected.icon

  return (
    <Badge
      className={cn(
        "gap-1 rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.18em]",
        selected.className,
      )}
    >
      <Icon className="h-3.5 w-3.5" />
      <span>{getTranslationLabel(value as TranslationStatus, t)}</span>
    </Badge>
  )
}
