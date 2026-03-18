import { NavLink, useLocation } from "react-router-dom"
import { BookOpenText, Calendar, ChevronRight, FileText, Orbit, PenSquare, Settings, User } from "lucide-react"
import { useTranslation } from "react-i18next"

import {
    Sidebar,
    SidebarContent,
    SidebarGroup,
    SidebarGroupContent,
    SidebarGroupLabel,
    SidebarMenu,
    SidebarMenuButton,
    SidebarMenuItem,
    SidebarFooter,
    SidebarHeader,
    useSidebar,
} from "@/components/ui/sidebar"

const items = [
    {
        titleKey: "community.nav.community",
        url: "/",
        icon: BookOpenText,
    },
    {
        titleKey: "community.nav.newTranslation",
        url: "/translate",
        icon: PenSquare,
    },
    {
        titleKey: "history.history",
        url: "/history",
        icon: Calendar,
    },
    {
        titleKey: "glossary.glossary_management",
        url: "/glossary",
        icon: FileText,
    },
    {
        titleKey: "settings.title",
        url: "/settings",
        icon: Settings,
    },
]

export function AppSidebar() {
    const { state } = useSidebar()
    const location = useLocation()
    const { t } = useTranslation()
    return (
        <Sidebar
            collapsible="icon"
            className="border-r border-white/8 bg-[#181818] text-slate-100"
        >
            <SidebarHeader>
                <div className="px-2 py-2.5">
                    {state === "expanded" && (
                        <div className="rounded-[20px] border border-white/8 bg-[#1c1c1c] px-3 py-3 transition-all duration-200">
                            <div className="flex items-center gap-3">
                                <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/[0.03]">
                                    <Orbit className="h-4.5 w-4.5 text-slate-300" />
                                </div>
                                <div>
                                    <h1 className="text-lg font-semibold tracking-tight text-white">
                                        LaTeXTrans
                                    </h1>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </SidebarHeader>
            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupLabel className="px-2 pb-2 text-[11px] uppercase tracking-[0.24em] text-slate-500">
                        {t("layout.menu")}
                    </SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {items.map((item) => (
                                <SidebarMenuItem key={item.titleKey}>
                                    <SidebarMenuButton
                                        asChild
                                        isActive={
                                            item.url === "/"
                                                ? location.pathname === "/"
                                                : location.pathname.startsWith(item.url)
                                        }
                                        className="h-11 rounded-2xl px-3 text-slate-300 transition hover:bg-white/[0.03] hover:text-white data-[active=true]:bg-slate-500/12 data-[active=true]:text-slate-50 data-[active=true]:shadow-[inset_0_0_0_1px_rgba(148,163,184,0.22)]"
                                    >
                                        <NavLink to={item.url}>
                                            <item.icon />
                                            <span>{t(item.titleKey)}</span>
                                            {state === "expanded" && item.url === "/" ? (
                                                <ChevronRight className="ml-auto h-4 w-4 text-slate-500" />
                                            ) : null}
                                        </NavLink>
                                    </SidebarMenuButton>
                                </SidebarMenuItem>
                            ))}
                        </SidebarMenu>
                    </SidebarGroupContent>
                </SidebarGroup>
            </SidebarContent>
            <SidebarFooter>
                <SidebarMenu>
                    <SidebarMenuItem>
                        <SidebarMenuButton
                            asChild
                            isActive={location.pathname.startsWith("/profile")}
                            className="h-11 rounded-2xl px-3 text-slate-300 transition hover:bg-white/[0.03] hover:text-white data-[active=true]:bg-slate-500/12 data-[active=true]:text-slate-50"
                        >
                            <NavLink to="/profile">
                                <User />
                                <span>{t("layout.profile")}</span>
                            </NavLink>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarFooter>
        </Sidebar>
    )
}
