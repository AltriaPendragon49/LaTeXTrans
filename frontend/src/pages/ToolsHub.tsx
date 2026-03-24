import { useMemo } from "react"
import { useSearchParams, Link } from "react-router-dom"
import { useTranslation } from "react-i18next"

import Dashboard from "@/pages/Dashboard"
import HistoryPage from "@/pages/History"
import SettingsPage from "@/pages/Settings"

function GlossaryPanel() {
  const { t } = useTranslation()
  return <div className="rounded-[24px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-6">{t("glossary.glossary_management")}</div>
}

type ToolPanel = "translate" | "history" | "settings" | "glossary"

export default function ToolsHubPage() {
  const { t } = useTranslation()
  const [searchParams] = useSearchParams()
  const panel = (searchParams.get("panel") ?? "translate") as ToolPanel

  const panels = useMemo(
    () => [
      { key: "translate" as const, label: t("dashboard.start_translation") },
      { key: "history" as const, label: t("history.history") },
      { key: "settings" as const, label: t("settings.title") },
      { key: "glossary" as const, label: t("glossary.glossary_management") },
    ],
    [t],
  )

  return (
    <div className="min-h-full space-y-4 bg-[var(--shell-bg)] px-4 py-6 text-[var(--shell-text)] sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-4">
        <div className="rounded-[24px] border border-[color:var(--shell-border)] bg-[var(--shell-surface)] p-4">
          <div className="flex flex-wrap gap-2">
            {panels.map((entry) => (
              <Link
                key={entry.key}
                to={`/tools?panel=${entry.key}`}
                className={`rounded-full px-4 py-2 text-sm ${panel === entry.key ? "bg-slate-500/14 text-[var(--shell-heading)] shadow-[inset_0_0_0_1px_var(--shell-border)]" : "border border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-text-soft)]"}`}
              >
                {entry.label}
              </Link>
            ))}
          </div>
        </div>

        {panel === "history" ? (
          <HistoryPage />
        ) : panel === "settings" ? (
          <SettingsPage />
        ) : panel === "glossary" ? (
          <GlossaryPanel />
        ) : (
          <Dashboard />
        )}
      </div>
    </div>
  )
}
