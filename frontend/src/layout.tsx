import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { Outlet, useLocation, useNavigate } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import { LogIn, Loader2, PenSquare, User } from "lucide-react"
import { useTranslation } from "react-i18next"
import { LanguageSelector } from "@/components/LanguageSelector"

export default function Layout() {
    const navigate = useNavigate()
    const location = useLocation()
    const { user, isAuthenticated, loading, isSupabaseAvailable } = useAuth()
    const { t } = useTranslation()
    const isCommunityRoute = location.pathname === "/" || location.pathname.startsWith("/paper/")
    const title = isCommunityRoute ? t("community.feed.title") : t("community.nav.newTranslation")
    const subtitle = isCommunityRoute ? "" : t("common.new_translation")

    return (
        <div className="dark min-h-screen bg-[#151515] text-slate-100">
            <SidebarProvider>
                <AppSidebar />
                <main className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden bg-transparent">
                    <div className="sticky top-0 z-10 border-b border-white/8 bg-[#161616]/90 px-4 py-3 shadow-[0_18px_40px_-36px_rgba(0,0,0,0.8)] backdrop-blur">
                        <div className="flex items-center justify-between gap-4">
                            <div className="flex min-w-0 items-center gap-3">
                                <SidebarTrigger className="h-10 w-10 rounded-2xl border border-white/10 bg-white/[0.03] text-slate-100 hover:bg-white/[0.06]" />
                                <div className="min-w-0">
                                    {subtitle ? (
                                        <div className="flex items-center gap-2">
                                            <PenSquare className="h-4 w-4 text-slate-400" />
                                            <p className="truncate text-xs uppercase tracking-[0.22em] text-slate-500">
                                                {subtitle}
                                            </p>
                                        </div>
                                    ) : null}
                                    <div className="truncate text-base font-semibold tracking-tight text-white">
                                        {title}
                                    </div>
                                </div>
                            </div>

                            <div className="flex items-center gap-2 pr-1">
                                <LanguageSelector />
                                {loading ? (
                                    <Loader2 className="h-4 w-4 animate-spin text-slate-400" />
                                ) : isAuthenticated ? (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => navigate('/profile')}
                                        className="h-11 rounded-2xl border border-white/10 bg-white/[0.03] px-3 text-slate-100 hover:bg-white/[0.06]"
                                    >
                                        <User className="h-4 w-4" />
                                        <span className="max-w-[120px] truncate text-sm">
                                            {user?.email?.split('@')[0]}
                                        </span>
                                    </Button>
                                ) : isSupabaseAvailable ? (
                                    <Button
                                        variant="outline"
                                        size="sm"
                                        onClick={() => navigate('/login')}
                                        className="h-11 rounded-2xl border-white/10 bg-white/[0.03] px-4 text-slate-100 hover:bg-white/[0.06]"
                                    >
                                        <LogIn className="h-4 w-4" />
                                        {t("common.actions.signIn")}
                                    </Button>
                                ) : (
                                    <span className="rounded-full border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-slate-400">
                                        {t("layout.guestMode")}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                    <div className="flex-1 overflow-auto">
                        <Outlet />
                    </div>
                </main>
                <Toaster />
            </SidebarProvider>
        </div>
    )
}
