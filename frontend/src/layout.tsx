import { useTranslation } from "react-i18next"
import { Link, Outlet, useLocation } from "react-router-dom"

import { useIsMobile } from "@/hooks/use-mobile"
import { AppSidebar } from "@/layout/AppSidebar"
import { getMobilePrimaryNavItems, renderShellNavItemIcon } from "@/layout/shell-navigation"
import { Toaster } from "@/ui/primitives/sonner"

/** 主布局组件：根据设备类型展示桌面侧边栏或移动端底部导航，包含 Outlet 路由出口 */
export default function Layout() {
  const isMobile = useIsMobile()
  const location = useLocation()
  const { t } = useTranslation()
  const mobileNavItems = getMobilePrimaryNavItems({
    pathname: location.pathname,
    t,
  })

  return (
    <div className="flex h-[100dvh] overflow-hidden bg-[color:var(--px-shell-bg)] text-[color:var(--px-shell-ink)] selection:bg-[color:var(--px-shell-accent)] selection:text-white">
      {isMobile ? null : <AppSidebar />}
      <div className="min-w-0 flex-1 flex flex-col min-h-0">
        <main className="min-w-0 flex-1 flex flex-col min-h-0">
          <div
            className="flex-1 overflow-auto flex flex-col min-h-0"
            style={isMobile ? { paddingBottom: "calc(5.75rem + env(safe-area-inset-bottom))" } : undefined}
          >
            <Outlet />
          </div>
        </main>

        {isMobile ? (
          <nav
            data-testid="mobile-bottom-nav"
            aria-label={t("community.nav.explore", "Primary navigation")}
            className="fixed inset-x-0 bottom-0 z-30 border-t border-[color:var(--px-shell-line)]/80 bg-[color:color-mix(in_srgb,var(--px-shell-panel)_92%,white)] px-3 pt-3 shadow-[0_-22px_48px_-34px_rgba(15,23,42,0.36)] backdrop-blur-xl"
            style={{ paddingBottom: "calc(0.7rem + env(safe-area-inset-bottom))" }}
          >
            <div className="mx-auto grid max-w-xl grid-cols-4 gap-2">
              {mobileNavItems.map((item) => {
                return (
                  <Link
                    key={item.key}
                    to={item.to}
                    aria-label={item.label}
                    className={`flex min-h-[3.75rem] flex-col items-center justify-center gap-1 rounded-[20px] px-2 py-2 text-center text-[11px] font-semibold transition-colors ${
                      item.active
                        ? "bg-[color:var(--px-shell-accent)] text-white shadow-[0_18px_34px_-24px_rgba(0,55,176,0.62)]"
                        : "bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-muted)]"
                    }`}
                  >
                    {renderShellNavItemIcon(item, "h-4 w-4")}
                    <span className="leading-tight">{item.label}</span>
                  </Link>
                )
              })}
            </div>
          </nav>
        ) : null}
      </div>
      <Toaster />
    </div>
  )
}
