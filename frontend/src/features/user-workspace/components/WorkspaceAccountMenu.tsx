import { useMemo } from "react"
import { LogOut, Settings, Shield, User as UserIcon, Wrench } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import userLogo from "../../../../userlogo.png"

import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import { useAuth } from "@/contexts/AuthContext"
import { getUserLoginInfo } from "@/features/user-workspace/accountIdentity"
import { Button } from "@/ui/button/Button"
import { Popover, PopoverContent, PopoverTrigger } from "@/ui/primitives/popover"
import type { QuotaSnapshot } from "@/lib/local-auth"

function formatLatexQuota(snapshot: QuotaSnapshot | null | undefined, loading: boolean, t: (key: string, values?: Record<string, unknown>) => string) {
  if (snapshot) {
    return `${snapshot.latex_translation.remaining}/${snapshot.latex_translation.limit}`
  }

  return loading ? t("profile.quota.loading") : t("profile.quota.unavailable")
}

function formatPdfDirectQuota(snapshot: QuotaSnapshot | null | undefined, loading: boolean, t: (key: string, values?: Record<string, unknown>) => string) {
  const pdfDirect = snapshot?.pdf_direct
  if (!pdfDirect) {
    return loading ? t("profile.quota.loading") : t("profile.quota.unavailable")
  }

  if (pdfDirect.status === "stale" && pdfDirect.unused_integral !== null) {
    return t("profile.quota.stalePointsValue", { value: pdfDirect.unused_integral })
  }

  if (pdfDirect.status === "stale") {
    return t("profile.quota.stale")
  }

  if (pdfDirect.unused_integral !== null && pdfDirect.status !== "unavailable") {
    return t("profile.quota.pointsValue", { value: pdfDirect.unused_integral })
  }

  return t("profile.quota.unavailable")
}

function QuotaCells({
  latexValue,
  pdfDirectValue,
}: {
  latexValue: string
  pdfDirectValue: string
}) {
  const { t } = useTranslation()

  return (
    <span
      className="mt-3 grid w-full grid-cols-2 gap-2"
      aria-label={t("profile.quota.summaryAria", {
        latexValue,
        pdfValue: pdfDirectValue,
      })}
    >
      <span className="min-w-0 rounded-[14px] border border-[color:var(--px-shell-line)] bg-white/65 px-2.5 py-2">
        <span className="block truncate text-[10px] font-bold text-[color:var(--px-shell-muted)]">
          {t("profile.quota.latexLabel")}
        </span>
        <span className="block truncate font-mono text-xs font-bold text-[color:var(--px-shell-ink)]">
          {latexValue}
        </span>
      </span>
      <span className="min-w-0 rounded-[14px] border border-[color:var(--px-shell-line)] bg-white/65 px-2.5 py-2">
        <span className="block truncate text-[10px] font-bold text-[color:var(--px-shell-muted)]">
          {t("profile.quota.pdfDirectLabel")}
        </span>
        <span className="block truncate font-mono text-xs font-bold text-[color:var(--px-shell-ink)]">
          {pdfDirectValue}
        </span>
      </span>
    </span>
  )
}

export function WorkspaceAccountMenu({ collapsed = false }: { collapsed?: boolean }) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { loading, quotaSnapshot, user, isAuthenticated, signOut } = useAuth()
  const isAdmin = hasAdminRole(user?.roles)
  const loginInfo = getUserLoginInfo(user)
  const menuLabel = t("profile.settings_and_account")
  const latexQuotaValue = formatLatexQuota(quotaSnapshot, loading, t)
  const pdfDirectQuotaValue = formatPdfDirectQuota(quotaSnapshot, loading, t)

  const profileLabel = useMemo(
    () => loginInfo || t("common.labels.user"),
    [loginInfo, t],
  )
  async function handleSignOut() {
    await signOut()
    navigate("/")
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={profileLabel}
          title={profileLabel}
          className={`flex w-full items-center rounded-[18px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] transition-all duration-200 hover:border-[color:var(--px-shell-accent)]/24 hover:bg-white ${
            collapsed ? "justify-center px-0 py-2.5" : "flex-col px-3 py-3"
          }`}
        >
          <span className={collapsed ? "flex items-center justify-center" : "flex w-full items-center gap-3"}>
            <span className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full bg-[color:var(--px-shell-accent-soft)]">
              <img
                src={userLogo}
                alt={t("profile.settings_and_account")}
                className="h-full w-full object-cover"
              />
            </span>
            <span className={collapsed ? "sr-only" : "min-w-0 flex-1 text-left"}>
              <span className="block truncate text-sm font-semibold text-[color:var(--px-shell-ink)]">
                {menuLabel}
              </span>
            </span>
          </span>
          {isAuthenticated && !collapsed ? (
            <QuotaCells latexValue={latexQuotaValue} pdfDirectValue={pdfDirectQuotaValue} />
          ) : null}
        </button>
      </PopoverTrigger>

      <PopoverContent
        side="top"
        align="start"
        sideOffset={12}
        className="w-72 rounded-[24px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-3 shadow-[0_30px_70px_-42px_rgba(15,23,42,0.45)]"
      >
        <div className="rounded-[18px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-4 py-3">
          <p className="text-[10px] font-black uppercase tracking-[0.22em] text-[color:var(--px-shell-muted)]">
            {menuLabel}
          </p>
          <p className="mt-1 truncate text-base font-semibold text-[color:var(--px-shell-ink)]">
            {profileLabel}
          </p>
          {isAuthenticated ? (
            <QuotaCells latexValue={latexQuotaValue} pdfDirectValue={pdfDirectQuotaValue} />
          ) : null}
        </div>

        <div className="mt-3 space-y-2">
          {isAuthenticated ? (
            <>
              <Link
                to="/profile"
                className="flex items-center gap-3 rounded-[16px] px-3 py-3 text-sm font-medium text-[color:var(--px-shell-ink)] transition-colors hover:bg-[color:var(--px-shell-accent-soft)]"
              >
                <UserIcon className="h-4 w-4" />
                <span>{menuLabel}</span>
              </Link>
              <Link
                to="/workspace/settings"
                className="flex items-center gap-3 rounded-[16px] px-3 py-3 text-sm font-medium text-[color:var(--px-shell-ink)] transition-colors hover:bg-[color:var(--px-shell-accent-soft)]"
              >
                <Settings className="h-4 w-4" />
                <span>{t("settings.title")}</span>
              </Link>
              {isAdmin ? (
                <>
                  <Link
                    to="/admin/curation"
                    className="flex items-center gap-3 rounded-[16px] px-3 py-3 text-sm font-medium text-[color:var(--px-shell-ink)] transition-colors hover:bg-[color:var(--px-shell-accent-soft)]"
                  >
                    <Shield className="h-4 w-4" />
                    <span>{t("community.admin.nav.curation", "Admin curation")}</span>
                  </Link>
                  <Link
                    to="/admin/curation/tasks"
                    className="flex items-center gap-3 rounded-[16px] px-3 py-3 text-sm font-medium text-[color:var(--px-shell-ink)] transition-colors hover:bg-[color:var(--px-shell-accent-soft)]"
                  >
                    <Wrench className="h-4 w-4" />
                    <span>{t("community.admin.nav.tasks", "Admin tasks")}</span>
                  </Link>
                </>
              ) : null}
              <Button
                type="button"
                variant="ghost"
                className="w-full justify-start rounded-[16px] border border-transparent px-3"
                onClick={() => void handleSignOut()}
              >
                <LogOut className="h-4 w-4" />
                {t("profile.sign_out")}
              </Button>
            </>
          ) : (
            <Button
              type="button"
              className="w-full justify-start rounded-[16px]"
              onClick={() => navigate("/login")}
            >
              <UserIcon className="h-4 w-4" />
              {t("common.actions.signIn")}
            </Button>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}
