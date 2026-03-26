import type { CSSProperties } from "react"
import { BookOpenText, Orbit, PenSquare } from "lucide-react"
import { NavLink, useLocation } from "react-router-dom"
import { useTranslation } from "react-i18next"

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarTrigger,
} from "@/components/ui/sidebar"

const items = [
  {
    titleKey: "community.nav.community",
    url: "/",
    icon: BookOpenText,
  },
]

export function AppSidebar() {
  const location = useLocation()
  const { t } = useTranslation()

  return (
    <Sidebar
      variant="floating"
      collapsible="icon"
      style={
        {
          "--sidebar-width": "13.5rem",
          "--sidebar-width-icon": "3.75rem",
          "--sidebar-gap-offset": "0.75rem",
        } as CSSProperties
      }
      className="m-3 rounded-[28px] border border-[color:var(--shell-border)]/60 bg-[color:color-mix(in_srgb,var(--shell-surface)_94%,transparent)] text-[var(--shell-heading)] shadow-[0_22px_52px_rgba(15,23,42,0.045)] backdrop-blur-md"
    >
      <SidebarHeader className="px-2.5 pb-2 pt-2.5">
        <NavLink
          to="/"
          aria-label="LaTeXTrans Community"
          title="LaTeXTrans Community"
          className="flex items-center gap-3 rounded-[18px] px-2.5 py-2 transition hover:bg-[var(--shell-pill)]"
        >
          <div className="flex h-9.5 w-9.5 items-center justify-center rounded-[18px] border border-[color:var(--shell-border)]/60 bg-[var(--shell-pill)] shadow-[inset_0_1px_0_rgba(255,255,255,0.45)]">
            <Orbit className="h-4.5 w-4.5 text-[var(--shell-icon)]" />
          </div>
          <div className="min-w-0 flex-1 group-data-[collapsible=icon]:hidden">
            <p className="truncate text-sm font-semibold tracking-tight text-[var(--shell-heading)]">
              LaTeXTrans
            </p>
            <p className="truncate text-[11px] uppercase tracking-[0.18em] text-[var(--shell-text-muted)]">
              {t("community.conversation.title")}
            </p>
          </div>
        </NavLink>
        <div className="mt-1 flex justify-center group-data-[collapsible=icon]:justify-center">
          <SidebarTrigger className="h-8 w-8 rounded-xl border border-[color:var(--shell-border)] bg-[var(--shell-pill)] text-[var(--shell-heading)] transition-colors hover:bg-[var(--shell-pill-hover)]" />
        </div>
      </SidebarHeader>

      <SidebarContent className="px-2.5 pt-1">
        <div className="px-2 pb-2 text-[10px] uppercase tracking-[0.2em] text-[var(--shell-text-muted)] group-data-[collapsible=icon]:hidden">
          Workspace
        </div>
        <SidebarMenu className="items-stretch">
          {items.map((item) => (
            <SidebarMenuItem key={item.titleKey}>
              <SidebarMenuButton
                asChild
                isActive={item.url === "/" ? location.pathname === "/" : location.pathname.startsWith(item.url)}
                className="h-11 rounded-[17px] px-3 text-[var(--shell-text-soft)] transition hover:bg-[var(--shell-pill)] hover:text-[var(--shell-heading)] data-[active=true]:bg-[var(--shell-pill-hover)] data-[active=true]:text-[var(--shell-heading)] data-[active=true]:shadow-[inset_0_0_0_1px_var(--shell-border)]"
              >
                <NavLink to={item.url} aria-label={t(item.titleKey)} title={t(item.titleKey)} className="flex items-center gap-3">
                  <item.icon />
                  <span className="group-data-[collapsible=icon]:hidden">{t(item.titleKey)}</span>
                </NavLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>

      <SidebarFooter className="px-2.5 pb-2.5 pt-2">
        <div className="border-t border-[color:var(--shell-border)]/70 pt-2">
          <div className="px-2 pb-2 text-[10px] uppercase tracking-[0.2em] text-[var(--shell-text-muted)] group-data-[collapsible=icon]:hidden">
            Tools
          </div>
          <SidebarMenu className="items-stretch">
            <SidebarMenuItem>
              <SidebarMenuButton
                asChild
                isActive={location.pathname.startsWith("/tools")}
                className="h-11 rounded-[17px] px-3 text-[var(--shell-text-soft)] transition hover:bg-[var(--shell-pill)] hover:text-[var(--shell-heading)] data-[active=true]:bg-[var(--shell-pill-hover)] data-[active=true]:text-[var(--shell-heading)]"
              >
                <NavLink
                  to="/tools?panel=translate"
                  aria-label={t("community.nav.paperTools")}
                  title={t("community.nav.paperTools")}
                  className="flex items-center gap-3"
                >
                  <PenSquare />
                  <span className="group-data-[collapsible=icon]:hidden">{t("community.nav.paperTools")}</span>
                </NavLink>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </div>
      </SidebarFooter>
    </Sidebar>
  )
}
