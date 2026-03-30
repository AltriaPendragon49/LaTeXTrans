import { Compass, MessageSquare, PenSquare, User, Settings } from "lucide-react"
import { NavLink, useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"
import { useAuth } from "@/contexts/AuthContext"

export function AppSidebar() {
  const { t } = useTranslation()
  const { user, isAuthenticated, isSupabaseAvailable } = useAuth()
  const navigate = useNavigate()

  return (
    <nav className="fixed left-0 top-0 h-full flex flex-col justify-between py-8 px-4 z-50 backdrop-blur-xl bg-surface dark:bg-slate-900 w-20 hover:w-64 transition-all duration-300 ease-in-out border-none group shadow-[0_20px_40px_rgba(27,28,28,0.06)]">
      <div className="flex flex-col gap-8 items-center group-hover:items-start group-hover:px-4">
        <div className="text-lg font-bold text-primary tracking-tighter mb-4 flex items-center justify-center">
          <span className="group-hover:hidden">LT</span>
          <span className="hidden group-hover:block whitespace-nowrap">LaTexTrans</span>
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
            to="/agent" 
            className={({isActive}) => `flex items-center gap-4 rounded-full px-4 py-3 transition-colors group/item ${isActive ? 'bg-primary/10 text-primary border-l-4 border-primary' : 'text-tertiary hover:bg-surface-container-low'}`}
          >
            <MessageSquare className="w-6 h-6 shrink-0" />
            <span className="hidden group-hover:block font-inter text-sm tracking-tight font-medium uppercase whitespace-nowrap">{t("community.conversation.title", "Conversation")}</span>
          </NavLink>

          <NavLink 
            to="/tools" 
            className={({isActive}) => `flex items-center gap-4 rounded-full px-4 py-3 transition-colors group/item ${isActive ? 'bg-primary/10 text-primary border-l-4 border-primary' : 'text-tertiary hover:bg-surface-container-low'}`}
          >
            <PenSquare className="w-6 h-6 shrink-0" />
            <span className="hidden group-hover:block font-inter text-sm tracking-tight font-medium uppercase whitespace-nowrap">{t("community.nav.paperTools", "Tools")}</span>
          </NavLink>
        </div>


      </div>

      <div className="flex flex-col gap-4 items-center group-hover:items-start group-hover:px-4">
        {isSupabaseAvailable && !isAuthenticated && (
          <button onClick={() => navigate('/login')} className="flex items-center gap-4 text-tertiary hover:bg-surface-container-low rounded-full px-4 py-3 transition-colors w-full justify-center group-hover:justify-start">
            <User className="w-6 h-6 shrink-0" />
            <span className="hidden group-hover:block font-inter text-sm tracking-tight font-medium uppercase whitespace-nowrap">{t("common.actions.signIn", "Sign In")}</span>
          </button>
        )}
        
        <button onClick={() => navigate('/settings')} className="flex items-center gap-4 text-tertiary hover:bg-surface-container-low rounded-full px-4 py-3 transition-colors w-full justify-center group-hover:justify-start">
          <Settings className="w-6 h-6 shrink-0" />
          <span className="hidden group-hover:block font-inter text-sm tracking-tight font-medium uppercase whitespace-nowrap">Settings</span>
        </button>

        {isAuthenticated && user && (
          <button onClick={() => navigate('/profile')} className="mt-4 flex items-center gap-3 hover:bg-surface-container-low rounded-full group-hover:p-2 w-full justify-center group-hover:justify-start transition-all border-none text-left">
            <div className="w-8 h-8 rounded-full bg-primary/20 text-primary flex items-center justify-center shrink-0 uppercase font-bold text-xs border border-primary/30">
              {user.email?.charAt(0)}
            </div>
            <div className="hidden group-hover:flex flex-col min-w-0">
              <span className="text-xs font-bold text-on-surface truncate pr-2">{user.email?.split('@')[0]}</span>
              <span className="text-[10px] text-tertiary truncate pr-2">Pro Plan</span>
            </div>
          </button>
        )}
      </div>
    </nav>
  )
}
