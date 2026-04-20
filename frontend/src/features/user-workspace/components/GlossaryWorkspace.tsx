import { BookOpenText } from "lucide-react"
import { useTranslation } from "react-i18next"

import { PageIntro } from "@/ui/page-intro/PageIntro"
import { StatePanel } from "@/ui/state-panel/StatePanel"

export function GlossaryWorkspace() {
  const { t } = useTranslation()

  return (
    <div className="mx-auto max-w-5xl space-y-6 py-2">
      <PageIntro
        title={t("glossary.glossary_management")}
        description={t("glossary.managementComingSoon")}
      />

      <StatePanel
        className="py-14"
        icon={<BookOpenText className="h-7 w-7" />}
        title={t("glossary.glossary_management")}
        description={t("glossary.managementComingSoon")}
      />
    </div>
  )
}
