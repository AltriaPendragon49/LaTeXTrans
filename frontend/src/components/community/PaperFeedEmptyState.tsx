import { Inbox } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { Button } from "@/components/ui/button"

export function PaperFeedEmptyState() {
  const { t } = useTranslation()

  return (
    <div className="rounded-[32px] border border-dashed border-white/12 bg-slate-950/50 px-6 py-14 text-center">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-white/10 bg-white/[0.03]">
        <Inbox className="h-7 w-7 text-slate-300" />
      </div>
      <div className="mx-auto mt-5 max-w-xl space-y-2">
        <h2 className="text-2xl font-semibold text-white">{t("community.empty.title")}</h2>
        <p className="text-sm text-slate-400">{t("community.empty.description")}</p>
      </div>
      <Button
        asChild
        variant="outline"
        className="mt-6 h-11 rounded-2xl border-white/10 bg-white/[0.03] text-slate-100"
      >
        <Link to="/translate">{t("community.empty.cta")}</Link>
      </Button>
    </div>
  )
}
