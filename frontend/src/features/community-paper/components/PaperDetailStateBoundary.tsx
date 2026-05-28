import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"

import type { CommunityPaper } from "@/types/community"
import { StatePanel } from "@/ui/state-panel/StatePanel"

import { PaperDetailSkeleton } from "./PaperDetailSkeleton"

/** 论文详情状态边界 Props */
interface PaperDetailStateBoundaryProps {
  /** 是否正在加载 */
  loading: boolean
  /** 错误信息 */
  error: string | null
  /** 是否未找到 */
  notFound: boolean
  /** 论文数据 */
  paper: CommunityPaper | null
  /** 子渲染函数，仅在数据就绪时调用 */
  children: (paper: CommunityPaper) => ReactNode
}

/**
 * 论文详情状态边界组件
 * 根据加载/错误/未找到状态渲染对应的 UI（骨架屏、错误状态、404状态），
 * 数据就绪时将论文数据传递给子组件
 */
export function PaperDetailStateBoundary({
  loading,
  error,
  notFound,
  paper,
  children,
}: PaperDetailStateBoundaryProps) {
  const { t } = useTranslation()

  if (loading) {
    return <PaperDetailSkeleton />
  }

  if (error && !notFound) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 py-16">
        <StatePanel
          tone="danger"
          className="w-full max-w-lg py-12"
          title={t("community.detail.errorTitle")}
          description={t("community.detail.errorDescription")}
          detail={<p className="text-sm text-[color:var(--px-shell-danger)]">{error}</p>}
        />
      </div>
    )
  }

  if (notFound || !paper) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 py-16">
        <StatePanel
          className="w-full max-w-lg py-12"
          title={t("community.detail.notFoundTitle")}
          description={t("community.detail.notFoundDescription")}
        />
      </div>
    )
  }

  return <>{children(paper)}</>
}
