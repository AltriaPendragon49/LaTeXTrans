import { AppSidebar } from "@/components/app-sidebar"
import { Outlet } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { LanguageSelector } from "@/components/LanguageSelector"
import { ThemeToggle } from "@/components/ThemeToggle"

export default function Layout() {
    return (
        <div className="min-h-screen bg-background text-on-surface font-body selection:bg-primary-fixed selection:text-on-primary-fixed overflow-hidden">
            <AppSidebar />
            <main className="ml-20 min-h-screen flex flex-col transition-all duration-300">
                <div className="flex-1 overflow-auto flex flex-col">
                    <Outlet />
                </div>
            </main>
            <Toaster />
            
            <div className="fixed bottom-4 right-4 z-50 flex items-center gap-2 p-2 rounded-full bg-surface-container-highest shadow-md border border-outline-variant/20">
                <LanguageSelector />
                <ThemeToggle />
            </div>
        </div>
    )
}
