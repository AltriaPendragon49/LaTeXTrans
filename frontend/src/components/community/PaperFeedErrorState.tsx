import { AlertTriangle, RefreshCcw } from "lucide-react"
import { useTranslation } from "react-i18next"

import { Button } from "@/components/ui/button"

interface PaperFeedErrorStateProps {
  onRetry: () => void
}

export function PaperFeedErrorState({ onRetry }: PaperFeedErrorStateProps) {
  const { t } = useTranslation()

  return (
    <div className="rounded-[32px] border border-rose-500/20 bg-rose-500/5 px-6 py-14 text-center">
      <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full border border-rose-400/20 bg-rose-500/10">
        <AlertTriangle className="h-7 w-7 text-rose-700 dark:text-rose-200" />
      </div>
      <div className="mx-auto mt-5 max-w-xl space-y-2">
        <h2 className="text-2xl font-semibold text-rose-950 dark:text-white">{t("community.error.title")}</h2>
        <p className="text-sm text-rose-800/80 dark:text-slate-300">{t("community.error.description")}</p>
      </div>
      <Button
        type="button"
        onClick={onRetry}
        variant="outline"
        className="mt-6 h-11 rounded-2xl border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-heading)]"
      >
        <RefreshCcw className="h-4 w-4" />
        {t("community.error.retry")}
      </Button>
    </div>
  )
}
