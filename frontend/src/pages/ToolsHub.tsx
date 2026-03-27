import { useMemo } from "react"
import { useSearchParams, Link } from "react-router-dom"
import { useTranslation } from "react-i18next"

import Dashboard from "@/pages/Dashboard"
import HistoryPage from "@/pages/History"
import SettingsPage from "@/pages/Settings"

function GlossaryPanel() {
  const { t } = useTranslation()
  return (
    <div className="bg-surface-container-lowest rounded-2xl p-8 border border-outline-variant/10 shadow-sm">
      <h3 className="text-lg font-bold text-on-surface mb-6">{t("glossary.glossary_management")}</h3>
      <p className="text-sm text-tertiary">Management interface coming soon.</p>
    </div>
  )
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
    <div className="min-h-full bg-background transition-colors">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8 lg:py-12">
        <header className="mb-8 lg:mb-10">
          <h1 className="mb-2 text-3xl font-bold tracking-tighter text-on-surface lg:text-4xl">
            {t("navbar.tools")}
          </h1>
          <p className="max-w-xl text-sm text-tertiary lg:text-base">
            Direct access to the LaTexTrans ecosystem for high-fidelity document translation.
          </p>
        </header>

        <div className="mb-8 inline-flex max-w-full items-center overflow-x-auto rounded-full border border-outline-variant/30 bg-surface-container-low p-1.5 shadow-sm lg:mb-10">
          {panels.map((entry) => (
            <Link
              key={entry.key}
              to={`/tools?panel=${entry.key}`}
              className={`whitespace-nowrap px-4 py-2 text-sm font-semibold transition-all sm:px-6 lg:px-8 lg:py-2.5 lg:text-base rounded-full ${
                panel === entry.key
                  ? "bg-primary text-on-primary shadow-md"
                  : "text-tertiary hover:bg-surface-container-high hover:text-on-surface"
              }`}
            >
              {entry.label}
            </Link>
          ))}
        </div>

        <div>
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
    </div>
  )
}
