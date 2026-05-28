import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"

import { SectionHeading } from "@/ui/section-heading/SectionHeading"

/** 首页信息流区域组件：包含标题栏和子内容插槽 */
export function HomeFeedSection({ children }: { children: ReactNode }) {
  const { t } = useTranslation()

  return (
    <section id="home-feed" className="space-y-3">
      <SectionHeading
        eyebrow={t("community.feed.sort.latest")}
        title={t("community.feed.title")}
      />
      {children}
    </section>
  )
}
