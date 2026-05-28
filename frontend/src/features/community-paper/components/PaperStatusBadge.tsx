import { useTranslation } from "react-i18next"

import { cn } from "@/lib/utils"
import type { CommunityStatus, TranslationStatus } from "@/types/community"

/** 论文状态徽章 Props */
interface PaperStatusBadgeProps {
  /** 类型：社区状态或翻译状态 */
  kind: "community" | "translation"
  /** 状态值 */
  value: CommunityStatus | TranslationStatus
}

/** 根据社区状态返回中文标签 */
function getCommunityLabel(value: CommunityStatus, t: (key: string) => string) {
  switch (value) {
    case "official":
      return t("community.status.community.official")
    case "user_fallback":
      return t("community.status.community.user_fallback")
  }
}

/** 根据翻译状态返回中文标签 */
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

/**
 * 论文状态徽章组件
 * 展示论文的社区状态（官方/用户提交）或翻译状态（未开始/排队中/处理中/已完成/失败）
 */
export function PaperStatusBadge({ kind, value }: PaperStatusBadgeProps) {
  const { t } = useTranslation()

  if (kind === "community") {
    const isOfficial = value === "official"
    const colorClass = isOfficial
      ? "text-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)]"
      : "text-[color:var(--px-shell-muted)] bg-[color:var(--px-shell-panel-strong)]"

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
    not_started: "text-[color:var(--px-shell-muted)] bg-[color:var(--px-shell-panel-strong)]",
    queued: "text-[color:var(--px-shell-warning)] bg-[color:var(--px-shell-warning-soft)]",
    processing: "text-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent-soft)]",
    completed: "text-[color:var(--px-shell-success)] bg-[color:var(--px-shell-success-soft)]",
    failed: "text-[color:var(--px-shell-danger)] bg-[color:var(--px-shell-danger-soft)]",
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
