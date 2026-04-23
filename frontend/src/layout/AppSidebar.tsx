import { useEffect, useState } from "react"
import { useLocation, useNavigate } from "react-router-dom"
import { useTranslation } from "react-i18next"

import { useAuth } from "@/contexts/AuthContext"
import { hasAdminRole } from "@/features/admin-curation/utils/admin-access"
import { WorkspaceAccountMenu } from "@/features/user-workspace/components/WorkspaceAccountMenu"
import { getDesktopShellNavItems, renderShellNavItemIcon } from "@/layout/shell-navigation"
import { SidebarBrandButton } from "@/ui/sidebar-shell/SidebarBrandButton"
import { SidebarNavItem } from "@/ui/sidebar-shell/SidebarNavItem"
import { SidebarShell } from "@/ui/sidebar-shell/SidebarShell"

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
  const navItems = getDesktopShellNavItems({
    pathname: location.pathname,
    isAuthenticated,
    isAdmin,
    t,
  })

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
          {navItems.map((item) => (
            <SidebarNavItem
              key={item.key}
              to={item.to}
              icon={renderShellNavItemIcon(item, "h-5 w-5")}
              label={item.label}
              collapsed={collapsed}
              active={item.active}
            />
          ))}
        </nav>
      }
      utility={<WorkspaceAccountMenu collapsed={collapsed} />}
    />
  )
}
