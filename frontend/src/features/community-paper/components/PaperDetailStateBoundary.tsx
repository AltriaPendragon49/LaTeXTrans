import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"

import type { CommunityPaper } from "@/types/community"
import { StatePanel } from "@/ui/state-panel/StatePanel"

import { PaperDetailSkeleton } from "./PaperDetailSkeleton"

interface PaperDetailStateBoundaryProps {
  loading: boolean
  error: string | null
  notFound: boolean
  paper: CommunityPaper | null
  children: (paper: CommunityPaper) => ReactNode
}

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
