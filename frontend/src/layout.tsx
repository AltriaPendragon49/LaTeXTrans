import { AppSidebar } from "@/components/app-sidebar"
import { Outlet } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"


export default function Layout() {
    return (
        <div className="h-screen w-screen bg-background text-on-surface font-body selection:bg-primary-fixed selection:text-on-primary-fixed overflow-hidden">
            <AppSidebar />
            <main className="ml-20 h-screen flex flex-col transition-all duration-300">
                <div className="flex-1 overflow-auto flex flex-col relative">
                    <Outlet />
                </div>
            </main>
            <Toaster />
            

        </div>
    )
}
