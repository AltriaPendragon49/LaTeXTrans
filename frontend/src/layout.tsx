import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { Outlet, useNavigate } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { useAuth } from "@/contexts/AuthContext"
import { Button } from "@/components/ui/button"
import { User, LogIn, Loader2 } from "lucide-react"

export default function Layout() {
    const navigate = useNavigate()
    const { user, isAuthenticated, loading, isSupabaseAvailable } = useAuth()

    return (
        <SidebarProvider>
            <AppSidebar />
            <main className="flex-1 min-w-0 h-screen overflow-hidden flex flex-col bg-slate-50 dark:bg-slate-950">
                <div className="flex items-center justify-between p-2 border-b bg-white dark:bg-slate-900 shadow-sm z-10 sticky top-0">
                    <div className="flex items-center">
                        <SidebarTrigger />
                        <div className="ml-2 font-medium">LaTeX 翻译平台</div>
                    </div>

                    <div className="pr-2">
                        {loading ? (
                            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                        ) : isAuthenticated ? (
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => navigate('/profile')}
                                className="gap-2"
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
                                className="gap-2"
                            >
                                <LogIn className="h-4 w-4" />
                                登录
                            </Button>
                        ) : (
                            <span className="text-xs text-muted-foreground px-2">访客模式</span>
                        )}
                    </div>
                </div>
                <div className="flex-1 overflow-auto p-6">
                    <Outlet />
                </div>
            </main>
            <Toaster />
        </SidebarProvider>
    )
}
