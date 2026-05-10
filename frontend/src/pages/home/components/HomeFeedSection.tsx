import type { ReactNode } from "react"
import { useTranslation } from "react-i18next"

import { SectionHeading } from "@/ui/section-heading/SectionHeading"

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
