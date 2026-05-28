import { Inbox } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { Button } from "@/ui/button/Button"
import { StatePanel } from "@/ui/state-panel/StatePanel"

/**
 * 论文列表空状态组件
 * 当社区论文列表没有数据时显示，引导用户前往翻译页面提交论文
 */
export function PaperFeedEmptyState() {
  const { t } = useTranslation()

  return (
    <StatePanel
      borderStyle="dashed"
      icon={<Inbox className="h-7 w-7" />}
      title={t("community.empty.title")}
      description={t("community.empty.description")}
      actions={(
        <Button
          asChild
          variant="outline"
          className="h-11 rounded-2xl border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)]"
        >
          <Link to="/translate">{t("community.empty.cta")}</Link>
        </Button>
      )}
    />
  )
}
