import { ArrowRight, BookOpenText, PenTool, ScrollText } from "lucide-react"
import { Link } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { useAuth } from "@/contexts/AuthContext"
import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import { PanelShell } from "@/ui/panel-shell/PanelShell"
import { PageIntro } from "@/ui/page-intro/PageIntro"

const TOOL_LINKS = [
  {
    key: "translate",
    to: "/translate",
    icon: PenTool,
    descriptionKey: "community.actions.sectionDescription",
  },
  {
    key: "history",
    to: "/workspace/history",
    icon: ScrollText,
    descriptionKey: "history.sign_in_to_view_and_manage_all_translation_task_records",
  },
  {
    key: "glossary",
    to: "/workspace/glossary",
    icon: BookOpenText,
    descriptionKey: "glossary.technical_terms_extracted_from_and_used_in_this_document",
  },
] as const

const ADMIN_LINKS = [
  {
    key: "curation",
    to: "/admin/curation",
    icon: PenTool,
    titleKey: "community.admin.nav.curation",
    descriptionKey: "community.admin.curation.description",
  },
  {
    key: "tasks",
    to: "/admin/curation/tasks",
    icon: ScrollText,
    titleKey: "community.admin.nav.tasks",
    descriptionKey: "community.admin.tasks.description",
  },
] as const

export default function ToolsHubPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  const isAdmin = hasAdminRole(user?.roles)

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-5 md:px-6">
      <PanelShell tone="glass" className="space-y-5">
        <PageIntro
          eyebrow={t("community.nav.paperTool", "Paper Tool")}
          title={t("community.nav.paperTool", "Paper Tool")}
          icon={<PenTool className="h-5 w-5" />}
        />

        <div className="grid gap-3 md:grid-cols-3">
          {TOOL_LINKS.map((item) => {
            const Icon = item.icon
            const title =
              item.key === "translate"
                ? t("community.actions.translate")
                : item.key === "history"
                  ? t("history.history")
                  : t("glossary.glossary_management")

            return (
              <Link
                key={item.key}
                to={item.to}
                className="group rounded-[22px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-[color:var(--px-shell-accent)]/28 hover:shadow-[0_18px_38px_-30px_rgba(15,23,42,0.35)]"
              >
                <div className="flex items-center justify-between">
                  <span className="flex h-10 w-10 items-center justify-center rounded-[16px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-accent)]">
                    <Icon className="h-4 w-4" />
                  </span>
                  <ArrowRight className="h-4 w-4 text-[color:var(--px-shell-muted)] transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-[color:var(--px-shell-accent)]" />
                </div>
                <h2 className="mt-4 text-base font-semibold text-[color:var(--px-shell-ink)]">{title}</h2>
                <p className="mt-2 text-sm leading-6 text-[color:var(--px-shell-muted)]">
                  {t(item.descriptionKey)}
                </p>
              </Link>
            )
          })}
        </div>

        {isAdmin ? (
          <div className="space-y-3 border-t border-[color:var(--px-shell-line)] pt-5">
            <PageIntro
              eyebrow={t("community.admin.nav.curation")}
              title={t("community.admin.nav.curation")}
              description={t("community.admin.tasks.description")}
              icon={<ScrollText className="h-5 w-5" />}
            />

            <div className="grid gap-3 md:grid-cols-2">
              {ADMIN_LINKS.map((item) => {
                const Icon = item.icon

                return (
                  <Link
                    key={item.key}
                    to={item.to}
                    className="group rounded-[22px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-[color:var(--px-shell-accent)]/28 hover:shadow-[0_18px_38px_-30px_rgba(15,23,42,0.35)]"
                  >
                    <div className="flex items-center justify-between">
                      <span className="flex h-10 w-10 items-center justify-center rounded-[16px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-accent)]">
                        <Icon className="h-4 w-4" />
                      </span>
                      <ArrowRight className="h-4 w-4 text-[color:var(--px-shell-muted)] transition-transform duration-200 group-hover:translate-x-0.5 group-hover:text-[color:var(--px-shell-accent)]" />
                    </div>
                    <h2 className="mt-4 text-base font-semibold text-[color:var(--px-shell-ink)]">
                      {t(item.titleKey)}
                    </h2>
                    <p className="mt-2 text-sm leading-6 text-[color:var(--px-shell-muted)]">
                      {t(item.descriptionKey)}
                    </p>
                  </Link>
                )
              })}
            </div>
          </div>
        ) : null}
      </PanelShell>
    </div>
  )
}
