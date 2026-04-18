import { Compass, ListChecks, PenSquare, Settings, Shield, User } from "lucide-react"
import { NavLink, useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { useAuth } from "@/contexts/AuthContext"
import paperxLogo from "../../paperx.png"

function hasAdminRole(roles: string[] | null | undefined): boolean {
  if (!roles?.length) {
    return false
  }
  const adminRoles = new Set(["admin", "super_admin", "community_admin", "curation_admin"])
  return roles.some((role) => adminRoles.has(String(role).trim().toLowerCase()))
}

export function AppSidebar() {
  const { t } = useTranslation()
  const { user, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const isAdmin = hasAdminRole(user?.roles)
  const brandName = t("brand.name")
  const profileLabel =
    user?.display_name?.trim() ||
    user?.email?.split('@')[0] ||
    user?.external_user_id ||
    t("common.labels.user")
  const profileInitial = profileLabel.charAt(0).toUpperCase()

  return (
    <nav className="fixed left-0 top-0 h-full flex flex-col justify-between py-8 px-4 z-50 backdrop-blur-xl bg-surface dark:bg-slate-900 w-20 hover:w-64 transition-all duration-300 ease-in-out border-none group shadow-[0_20px_40px_rgba(27,28,28,0.06)]">
      <div className="flex flex-col gap-8 items-center group-hover:items-start group-hover:px-4">
        <div className="text-lg font-bold text-primary tracking-tighter mb-4 flex items-center justify-center">
          <img
            src={paperxLogo}
            alt={brandName}
            className="h-9 w-9 shrink-0 rounded-xl object-cover shadow-[0_12px_30px_rgba(0,55,176,0.18)]"
          />
          <span className="hidden group-hover:block whitespace-nowrap ml-3">{brandName}</span>
        </div>
        
        <div className="flex flex-col gap-4 w-full">
          <NavLink 
            to="/" 
            className={({isActive}) => `flex items-center gap-4 rounded-full px-4 py-3 transition-colors group/item ${isActive ? 'bg-primary/10 text-primary border-l-4 border-primary' : 'text-tertiary hover:bg-surface-container-low'}`}
          >
            <Compass className="w-6 h-6 shrink-0" />
            <span className="hidden group-hover:block font-inter text-sm tracking-tight font-medium uppercase whitespace-nowrap">{t("community.nav.community", "Explore")}</span>
          </NavLink>

          <NavLink 
            to="/tools" 
            className={({isActive}) => `flex items-center gap-4 rounded-full px-4 py-3 transition-colors group/item ${isActive ? 'bg-primary/10 text-primary border-l-4 border-primary' : 'text-tertiary hover:bg-surface-container-low'}`}
          >
            <PenSquare className="w-6 h-6 shrink-0" />
            <span className="hidden group-hover:block font-inter text-sm tracking-tight font-medium uppercase whitespace-nowrap">{t("community.nav.paperTools", "Tools")}</span>
          </NavLink>

          {isAdmin ? (
            <>
              <NavLink
                to="/admin/curation"
                className={({isActive}) => `flex items-center gap-4 rounded-full px-4 py-3 transition-colors group/item ${isActive ? 'bg-primary/10 text-primary border-l-4 border-primary' : 'text-tertiary hover:bg-surface-container-low'}`}
              >
                <Shield className="w-6 h-6 shrink-0" />
                <span className="hidden group-hover:block font-inter text-sm tracking-tight font-medium uppercase whitespace-nowrap">{t("community.admin.nav.curation", "Admin curation")}</span>
              </NavLink>
              <NavLink
                to="/admin/curation/tasks"
                className={({isActive}) => `flex items-center gap-4 rounded-full px-4 py-3 transition-colors group/item ${isActive ? 'bg-primary/10 text-primary border-l-4 border-primary' : 'text-tertiary hover:bg-surface-container-low'}`}
              >
                <ListChecks className="w-6 h-6 shrink-0" />
                <span className="hidden group-hover:block font-inter text-sm tracking-tight font-medium uppercase whitespace-nowrap">{t("community.admin.nav.tasks", "Admin tasks")}</span>
              </NavLink>
            </>
          ) : null}
        </div>


      </div>

      <div className="flex flex-col gap-4 items-center group-hover:items-start group-hover:px-4">
        {!isAuthenticated && (
          <button onClick={() => navigate('/login')} className="flex items-center gap-4 text-tertiary hover:bg-surface-container-low rounded-full px-4 py-3 transition-colors w-full justify-center group-hover:justify-start">
            <User className="w-6 h-6 shrink-0" />
            <span className="hidden group-hover:block font-inter text-sm tracking-tight font-medium uppercase whitespace-nowrap">{t("common.actions.signIn", "Sign In")}</span>
          </button>
        )}
        
        <button onClick={() => navigate('/settings')} className="flex items-center gap-4 text-tertiary hover:bg-surface-container-low rounded-full px-4 py-3 transition-colors w-full justify-center group-hover:justify-start">
          <Settings className="w-6 h-6 shrink-0" />
          <span className="hidden group-hover:block font-inter text-sm tracking-tight font-medium uppercase whitespace-nowrap">{t("settings.title")}</span>
        </button>

        {isAuthenticated && user && (
          <button onClick={() => navigate('/profile')} className="mt-4 flex items-center gap-3 hover:bg-surface-container-low rounded-full group-hover:p-2 w-full justify-center group-hover:justify-start transition-all border-none text-left">
            <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center shrink-0 uppercase font-bold text-xs border border-primary/30">
              {profileInitial}
            </div>
            <div className="hidden group-hover:flex flex-col min-w-0">
              <span className="text-xs font-bold text-on-surface truncate pr-2">{profileLabel}</span>
            </div>
          </button>
        )}
      </div>
    </nav>
  )
}
