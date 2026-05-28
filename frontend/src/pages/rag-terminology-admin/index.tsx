import { useTranslation } from "react-i18next"
import { BookText } from "lucide-react"

import { PageIntro } from "@/ui/page-intro/PageIntro"
import { TerminologyReviewPanel } from "@/features/rag-terminology/components/TerminologyReviewPanel"

/** RAG术语管理页面组件：展示 RAG 术语审核面板 */
export default function RagTerminologyAdminPage() {
  const { t } = useTranslation()

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 md:px-8">
      <div className="space-y-8 animate-in fade-in duration-500">
        <PageIntro
          icon={<BookText className="h-5 w-5" />}
          title={t("ragTerminology.adminPanel.title")}
          description={t("ragTerminology.adminPanel.description")}
        />

        <TerminologyReviewPanel />
      </div>
    </div>
  )
}
