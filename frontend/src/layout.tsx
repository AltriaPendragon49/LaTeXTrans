import { AppSidebar } from "@/layout/AppSidebar"
import { Outlet } from "react-router-dom"
import { Toaster } from "@/ui/primitives/sonner"

export default function Layout() {
  return (
    <div className="flex h-[100dvh] overflow-hidden bg-[color:var(--px-shell-bg)] text-[color:var(--px-shell-ink)] selection:bg-[color:var(--px-shell-accent)] selection:text-white">
      <AppSidebar />
      <main className="min-w-0 flex-1 flex flex-col min-h-0">
        <div className="flex-1 overflow-auto flex flex-col min-h-0">
          <Outlet />
        </div>
      </main>
      <Toaster />
    </div>
  )
}
