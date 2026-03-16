import { Link } from "react-router-dom"
import { Calendar, Search, Settings, FileText, User } from "lucide-react"
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
        titleKey: "common.new_translation",
        url: "/",
        icon: Search,
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
    const { t } = useTranslation()
    return (
        <Sidebar collapsible="icon">
            <SidebarHeader>
                <div className="px-2 py-4">
                    {state === "expanded" && (
                        <h1 className="text-xl font-bold bg-linear-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent transition-all duration-200">
                            LaTeXTrans
                        </h1>
                    )}
                </div>
            </SidebarHeader>
            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupLabel>{t("layout.menu")}</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {items.map((item) => (
                                <SidebarMenuItem key={item.titleKey}>
                                    <SidebarMenuButton asChild>
                                        <Link to={item.url}>
                                            <item.icon />
                                            <span>{t(item.titleKey)}</span>
                                        </Link>
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
                        <SidebarMenuButton asChild>
                            <Link to="/profile">
                                <User />
                                <span>{t("layout.profile")}</span>
                            </Link>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarFooter>
        </Sidebar>
    )
}
