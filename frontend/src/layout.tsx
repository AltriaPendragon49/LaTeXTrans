import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"
import { Outlet } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"

export default function Layout() {
    return (
        <SidebarProvider>
            <AppSidebar />
            <main className="flex-1 min-w-0 h-screen overflow-hidden flex flex-col bg-slate-50 dark:bg-slate-950">
                <div className="flex items-center p-2 border-b bg-white dark:bg-slate-900 shadow-sm z-10 sticky top-0">
                    <SidebarTrigger />
                    <div className="ml-2 font-medium">LaTeX Translation Platform</div>
                </div>
                <div className="flex-1 overflow-auto p-6">
                    <Outlet />
                </div>
            </main>
            <Toaster />
        </SidebarProvider>
    )
}
