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
      className="mt-1.5 grid w-full grid-cols-2 px-2"
      aria-label={t("profile.quota.summaryAria", {
        latexValue,
        pdfValue: pdfDirectValue,
      })}
    >
      <span className="min-w-0 py-1.5 pr-2 text-center">
        <span className="block truncate text-[10px] font-semibold text-[color:var(--px-shell-muted)]">
          {t("profile.quota.latexLabel")}
        </span>
        <span className="block truncate text-sm font-bold text-[color:var(--px-shell-ink)]">
          {latexValue}
        </span>
      </span>
      <span className="min-w-0 border-l border-[color:var(--px-shell-line)]/70 py-1.5 pl-2 text-center">
        <span className="block truncate text-[10px] font-semibold text-[color:var(--px-shell-muted)]">
          {t("profile.quota.pdfDirectLabel")}
        </span>
        <span className="block truncate text-sm font-bold text-[color:var(--px-shell-ink)]">
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

  const triggerContent = (
    <>
      <span
        className={
          collapsed
            ? "flex items-center justify-center"
            : "absolute left-1 top-1/2 flex -translate-y-1/2 items-center justify-center"
        }
      >
        <span className="flex h-10 w-10 shrink-0 items-center justify-center overflow-hidden rounded-full border border-transparent bg-[color:var(--px-shell-accent-soft)] transition-all duration-200 group-hover:border-[color:var(--px-shell-accent)]/24 group-hover:bg-white group-hover:shadow-[0_12px_28px_-22px_rgba(18,118,199,0.58)] group-focus-visible:border-[color:var(--px-shell-accent)]/35 group-focus-visible:bg-white">
          <img
            src={userLogo}
            alt={t("profile.settings_and_account")}
            className="h-full w-full object-cover"
          />
        </span>
      </span>
      <span className={collapsed ? "sr-only" : "min-w-0 max-w-[8.5rem] text-center"}>
        <span className="block truncate text-sm font-semibold text-[color:var(--px-shell-ink)] transition-colors duration-200 group-hover:text-[color:var(--px-shell-accent-strong)] group-focus-visible:text-[color:var(--px-shell-accent-strong)]">
          {menuLabel}
        </span>
      </span>
    </>
  )

  return (
    <Popover>
      {collapsed ? (
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-label={profileLabel}
            title={profileLabel}
            className="group flex w-full items-center justify-center rounded-[16px] px-0 py-3.5 text-[color:var(--px-shell-muted)] transition-all duration-200 hover:bg-[color:var(--px-shell-accent-soft)] hover:text-[color:var(--px-shell-ink)] focus-visible:bg-[color:var(--px-shell-accent-soft)] focus-visible:text-[color:var(--px-shell-ink)] focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/20"
          >
            {triggerContent}
          </button>
        </PopoverTrigger>
      ) : (
        <div className="w-full">
          <PopoverTrigger asChild>
            <button
              type="button"
              aria-label={profileLabel}
              title={profileLabel}
              className="group relative flex h-12 w-full items-center justify-center rounded-[16px] px-4 text-[color:var(--px-shell-muted)] transition-all duration-200 hover:bg-[color:var(--px-shell-accent-soft)] hover:text-[color:var(--px-shell-ink)] focus-visible:bg-[color:var(--px-shell-accent-soft)] focus-visible:text-[color:var(--px-shell-ink)]"
            >
              {triggerContent}
            </button>
          </PopoverTrigger>
          {isAuthenticated ? (
            <QuotaCells latexValue={latexQuotaValue} pdfDirectValue={pdfDirectQuotaValue} />
          ) : null}
        </div>
      )}

      <PopoverContent
        side="top"
        align="start"
        sideOffset={12}
        className="w-72 rounded-[24px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] p-3 shadow-[0_30px_70px_-42px_rgba(15,23,42,0.45)]"
      >
        <div className="px-3 py-2.5">
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
