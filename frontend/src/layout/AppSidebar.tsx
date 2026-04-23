import { useEffect, useState } from "react"
import { Bookmark, Compass, PenTool, Sparkles } from "lucide-react"
import { useLocation, useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { useAuth } from "@/contexts/AuthContext"
import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import { WorkspaceAccountMenu } from "@/features/user-workspace/components/WorkspaceAccountMenu"
import { SidebarBrandButton } from "@/ui/sidebar-shell/SidebarBrandButton"
import { SidebarNavItem } from "@/ui/sidebar-shell/SidebarNavItem"
import { SidebarShell } from "@/ui/sidebar-shell/SidebarShell"

function isCommunityRoute(pathname: string) {
  return pathname === "/" || pathname.startsWith("/paper/")
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

function isPaperCopilotRoute(pathname: string) {
  return pathname === "/agent" || pathname.startsWith("/agent/")
}

export function AppSidebar() {
  const { t } = useTranslation()
  const { isAuthenticated, user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const routeDefaultCollapsed = location.pathname.startsWith("/paper/")
  const [collapsed, setCollapsed] = useState(routeDefaultCollapsed)
  const [sidebarHovered, setSidebarHovered] = useState(false)
  const brandName = t("brand.name")
  const brandSubtitle = t("brand.subtitle")
  const isAdmin = hasAdminRole(user?.roles)

  useEffect(() => {
    setCollapsed(routeDefaultCollapsed)
  }, [routeDefaultCollapsed])

  useEffect(() => {
    if (!collapsed) {
      setSidebarHovered(false)
    }
  }, [collapsed])

  return (
    <SidebarShell
      brand={
        <SidebarBrandButton
          brandName={brandName}
          subtitle={brandSubtitle}
          collapsed={collapsed}
          showCollapsedActionHint={sidebarHovered}
          collapsedActionLabel="Expand sidebar"
          onClick={() => {
            if (collapsed) {
              setCollapsed(false)
              return
            }

            navigate("/")
          }}
        />
      }
      collapsed={collapsed}
      onToggleCollapse={() => setCollapsed((current) => !current)}
      onHoverChange={setSidebarHovered}
      collapseLabel="Collapse sidebar"
      nav={
        <nav aria-label={t("community.nav.explore")} className="space-y-2">
          <SidebarNavItem
            to="/"
            icon={<Compass className="h-5 w-5" />}
            label={t("community.nav.community", "Community")}
            collapsed={collapsed}
            active={isCommunityRoute(location.pathname)}
          />
          {isAuthenticated ? (
            <SidebarNavItem
              to="/favorites"
              icon={<Bookmark className="h-5 w-5" />}
              label={t("community.nav.favorites")}
              collapsed={collapsed}
              active={location.pathname === "/favorites" || location.pathname.startsWith("/favorites/")}
            />
          ) : null}
          <SidebarNavItem
            to="/tools"
            icon={<PenTool className="h-5 w-5" />}
            label={t("community.nav.paperTool", "Paper Tool")}
            collapsed={collapsed}
            active={isPaperToolRoute(location.pathname)}
          />
          {isAdmin ? (
            <SidebarNavItem
              to="/agent"
              icon={<Sparkles className="h-5 w-5" />}
              label={t("community.conversation.title", "Paper Copilot")}
              collapsed={collapsed}
              active={isPaperCopilotRoute(location.pathname)}
            />
          ) : null}
        </nav>
      }
      utility={<WorkspaceAccountMenu collapsed={collapsed} />}
    />
  )
}
