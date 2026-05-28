import { AlertTriangle, RefreshCcw } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"
import { StatePanel } from "@/ui/state-panel/StatePanel"

/** 论文列表错误状态 Props */
interface PaperFeedErrorStateProps {
  /** 重试回调 */
  onRetry: () => void
}

/**
 * 论文列表错误状态组件
 * 在社区论文列表加载失败时显示错误提示和重试按钮
 */
export function PaperFeedErrorState({ onRetry }: PaperFeedErrorStateProps) {
  const { t } = useTranslation()

  return (
    <StatePanel
      tone="danger"
      icon={<AlertTriangle className="h-7 w-7" />}
      title={t("community.error.title")}
      description={t("community.error.description")}
      actions={(
        <Button
          type="button"
          onClick={onRetry}
          variant="outline"
          className="h-11 rounded-2xl border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-ink)]"
        >
          <RefreshCcw className="h-4 w-4" />
          {t("community.error.retry")}
        </Button>
      )}
    />
  )
}
