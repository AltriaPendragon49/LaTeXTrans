import { useMemo } from "react"
import { LogOut, Settings, Shield, User as UserIcon, Wrench } from "lucide-react"
import { Link, useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/ui/button/Button"
import { Popover, PopoverContent, PopoverTrigger } from "@/ui/primitives/popover"

export function WorkspaceAccountMenu({ collapsed = false }: { collapsed?: boolean }) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const { user, isAuthenticated, signOut } = useAuth()
  const isAdmin = hasAdminRole(user?.roles)

  const profileLabel = useMemo(
    () =>
      user?.display_name?.trim() ||
      user?.email?.split("@")[0] ||
      user?.external_user_id ||
      t("common.labels.user"),
    [t, user?.display_name, user?.email, user?.external_user_id],
  )
  const profileInitial = profileLabel.charAt(0).toUpperCase()

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
            collapsed ? "justify-center px-0 py-2.5" : "gap-3 px-3 py-3"
          }`}
        >
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[color:var(--px-shell-accent-soft)] text-sm font-bold uppercase text-[color:var(--px-shell-accent)]">
            {profileInitial}
          </span>
          <span className={collapsed ? "sr-only" : "min-w-0 flex-1 text-left"}>
            <span className="block truncate text-sm font-semibold text-[color:var(--px-shell-ink)]">
              {profileLabel}
            </span>
            <span className="block text-xs text-[color:var(--px-shell-muted)]">
              {isAuthenticated ? t("profile.profile") : t("common.actions.signIn")}
            </span>
          </span>
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
            {t("common.labels.user")}
          </p>
          <p className="mt-1 truncate text-base font-semibold text-[color:var(--px-shell-ink)]">
            {profileLabel}
          </p>
        </div>

        <div className="mt-3 space-y-2">
          {isAuthenticated ? (
            <>
              <Link
                to="/profile"
                className="flex items-center gap-3 rounded-[16px] px-3 py-3 text-sm font-medium text-[color:var(--px-shell-ink)] transition-colors hover:bg-[color:var(--px-shell-accent-soft)]"
              >
                <UserIcon className="h-4 w-4" />
                <span>{t("profile.profile")}</span>
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
