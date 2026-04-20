import { useEffect, useState } from "react"
import { Compass, PenTool } from "lucide-react"
import { useLocation, useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { WorkspaceAccountMenu } from "@/features/user-workspace/components/WorkspaceAccountMenu"
import { SidebarBrandButton } from "@/ui/sidebar-shell/SidebarBrandButton"
import { SidebarNavItem } from "@/ui/sidebar-shell/SidebarNavItem"
import { SidebarShell } from "@/ui/sidebar-shell/SidebarShell"

function isCommunityRoute(pathname: string) {
  return pathname === "/" || pathname.startsWith("/paper/") || pathname.startsWith("/agent")
}

function isPaperToolRoute(pathname: string) {
  return (
    pathname === "/tools" ||
    pathname.startsWith("/translate") ||
    pathname.startsWith("/processing") ||
    pathname.startsWith("/preview") ||
    pathname.startsWith("/workspace/history") ||
    pathname.startsWith("/workspace/glossary")
  )
}

export function AppSidebar() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const routeDefaultCollapsed = location.pathname.startsWith("/paper/")
  const [collapsed, setCollapsed] = useState(routeDefaultCollapsed)
  const brandName = t("brand.name")
  const brandSubtitle = t("brand.subtitle")

  useEffect(() => {
    setCollapsed(routeDefaultCollapsed)
  }, [routeDefaultCollapsed])

  return (
    <SidebarShell
      brand={
        <SidebarBrandButton
          brandName={brandName}
          subtitle={brandSubtitle}
          collapsed={collapsed}
          onClick={() => navigate("/")}
        />
      }
      collapsed={collapsed}
      onToggleCollapse={() => setCollapsed((current) => !current)}
      collapseLabel="Collapse sidebar"
      expandLabel="Expand sidebar"
      nav={
        <nav aria-label={t("community.nav.explore")} className="space-y-2">
          <SidebarNavItem
            to="/"
            icon={<Compass className="h-5 w-5" />}
            label={t("community.nav.community", "Community")}
            collapsed={collapsed}
            active={isCommunityRoute(location.pathname)}
          />
          <SidebarNavItem
            to="/tools"
            icon={<PenTool className="h-5 w-5" />}
            label={t("community.nav.paperTool", "Paper Tool")}
            collapsed={collapsed}
            active={isPaperToolRoute(location.pathname)}
          />
        </nav>
      }
      utility={<WorkspaceAccountMenu collapsed={collapsed} />}
    />
  )
}
