import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { Outlet, useLocation, useNavigate } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import { LogIn, Loader2, PenSquare, User } from "lucide-react"
import { useTranslation } from "react-i18next"
import { LanguageSelector } from "@/components/LanguageSelector"
import { ThemeToggle } from "@/components/ThemeToggle"

export default function Layout() {
    const navigate = useNavigate()
    const location = useLocation()
    const { user, isAuthenticated, loading, isSupabaseAvailable } = useAuth()
    const { t } = useTranslation()
    const isCommunityRoute = location.pathname === "/" || location.pathname.startsWith("/paper/")
    const title = isCommunityRoute ? t("community.feed.title") : t("community.nav.newTranslation")
    const subtitle = isCommunityRoute ? "" : t("common.new_translation")

    return (
        <div className="min-h-screen bg-[var(--shell-bg)] text-[var(--shell-text)] transition-colors">
            <SidebarProvider>
                <AppSidebar />
                <main className="flex h-screen min-w-0 flex-1 flex-col overflow-hidden bg-transparent">
                    <div className="sticky top-0 z-10 border-b border-[color:var(--shell-border-strong)] bg-[var(--shell-surface)] px-4 py-3 shadow-[var(--shell-shadow)] backdrop-blur">
                        <div className="flex items-center justify-between gap-4">
                            <div className="flex min-w-0 items-center gap-3">
                                <SidebarTrigger className="h-10 w-10 rounded-2xl border border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-heading)] transition-colors hover:bg-[var(--shell-pill-hover)]" />
                                <div className="min-w-0">
                                    {subtitle ? (
                                        <div className="flex items-center gap-2">
                                            <PenSquare className="h-4 w-4 text-[var(--shell-icon)]" />
                                            <p className="truncate text-xs uppercase tracking-[0.22em] text-[var(--shell-text-muted)]">
                                                {subtitle}
                                            </p>
                                        </div>
                                    ) : null}
                                    <div className="truncate text-base font-semibold tracking-tight text-[var(--shell-heading)]">
                                        {title}
                                    </div>
                                </div>
                            </div>

                            <div className="flex flex-wrap items-center justify-end gap-2 pr-1">
                                <LanguageSelector />
                                <ThemeToggle />
                                {loading ? (
                                    <Loader2 className="h-4 w-4 animate-spin text-[var(--shell-icon)]" />
                                ) : isAuthenticated ? (
                                    <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => navigate('/profile')}
                                        className="h-11 rounded-2xl border border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 text-[var(--shell-heading)] transition-colors hover:bg-[var(--shell-pill-hover)]"
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
                                        className="h-11 rounded-2xl border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-4 text-[var(--shell-heading)] transition-colors hover:bg-[var(--shell-pill-hover)]"
                                    >
                                        <LogIn className="h-4 w-4" />
                                        {t("common.actions.signIn")}
                                    </Button>
                                ) : (
                                    <span className="rounded-full border border-[color:var(--shell-border)] bg-[var(--shell-pill)] px-3 py-2 text-xs text-[var(--shell-text-muted)]">
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
