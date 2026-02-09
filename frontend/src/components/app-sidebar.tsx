import { Link } from "react-router-dom"
import { Calendar, Search, Settings, FileText, User } from "lucide-react"

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

// Menu items.
const items = [
    {
        title: "新建翻译",
        url: "/",
        icon: Search,
    },
    {
        title: "历史记录",
        url: "/history",
        icon: Calendar,
    },
    {
        title: "术语库管理",
        url: "/glossary",
        icon: FileText,
    },
    {
        title: "系统设置",
        url: "/settings",
        icon: Settings,
    },
]

export function AppSidebar() {
    const { state } = useSidebar()
    return (
        <Sidebar collapsible="icon">
            <SidebarHeader>
                <div className="px-2 py-4">
                    {state === "expanded" && (
                        <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent transition-all duration-200">
                            LaTeXTrans 🚀
                        </h1>
                    )}
                </div>
            </SidebarHeader>
            <SidebarContent>
                <SidebarGroup>
                    <SidebarGroupLabel>Menu</SidebarGroupLabel>
                    <SidebarGroupContent>
                        <SidebarMenu>
                            {items.map((item) => (
                                <SidebarMenuItem key={item.title}>
                                    <SidebarMenuButton asChild>
                                        <Link to={item.url}>
                                            <item.icon />
                                            <span>{item.title}</span>
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
                                <span>个人配置</span>
                            </Link>
                        </SidebarMenuButton>
                    </SidebarMenuItem>
                </SidebarMenu>
            </SidebarFooter>
        </Sidebar>
    )
}
