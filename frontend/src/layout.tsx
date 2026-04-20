import { AppSidebar } from "@/layout/AppSidebar"
import { Outlet } from "react-router-dom"
import { Toaster } from "@/ui/primitives/sonner"

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-[color:var(--px-shell-bg)] text-[color:var(--px-shell-ink)] selection:bg-[color:var(--px-shell-accent)] selection:text-white">
      <AppSidebar />
      <main className="min-w-0 flex-1">
        <div className="min-h-screen overflow-auto">
          <Outlet />
        </div>
      </main>
      <Toaster />
    </div>
  )
}
