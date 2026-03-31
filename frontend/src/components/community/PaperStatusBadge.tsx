import { useTranslation } from "react-i18next"

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
    const colorClass = isOfficial 
      ? "text-primary bg-primary/10" 
      : "text-secondary bg-secondary/10"
      
    return (
      <span className={cn(
        "px-2 py-0.5 rounded text-[9px] font-black tracking-widest uppercase",
        colorClass
      )}>
        {getCommunityLabel(value as CommunityStatus, t)}
      </span>
    )
  }

  const config: Record<
    TranslationStatus,
    string
  > = {
    not_started: "text-tertiary bg-surface-container",
    queued: "text-outline bg-surface-container-high",
    processing: "text-secondary bg-secondary/10",
    completed: "text-primary bg-primary/10",
    failed: "text-error bg-error-container",
  }

  const selectedClass = config[value as TranslationStatus]

  return (
    <span
      className={cn(
        "px-2 py-0.5 rounded text-[9px] font-black tracking-widest uppercase",
        selectedClass,
      )}
    >
      {getTranslationLabel(value as TranslationStatus, t)}
    </span>
  )
}
