import type { ComponentType } from "react"
import type { TFunction } from "i18next"
import { Bookmark, Compass, PenTool, Sparkles } from "lucide-react"
import userLogo from "../../userlogo.png"

function MobileAccountNavIcon({ className, alt }: { className?: string; alt: string }) {
  return <img src={userLogo} alt={alt} className={className ? `${className} rounded-full object-cover` : "rounded-full object-cover"} />
}

function translate(t: TFunction, key: string, fallback: string) {
  return t(key, { defaultValue: fallback })
}

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

function isFavoritesRoute(pathname: string) {
  return pathname === "/favorites" || pathname.startsWith("/favorites/")
}

function isProfileRoute(pathname: string) {
  return pathname === "/profile" || pathname.startsWith("/workspace/settings")
}

export function isPaperCopilotRoute(pathname: string) {
  return pathname === "/agent" || pathname.startsWith("/agent/")
}

export interface ShellNavItem {
  key: string
  to: string
  label: string
  icon?: ComponentType<{ className?: string }>
  imageAlt?: string
  active: boolean
}

export function getDesktopShellNavItems({
  pathname,
  isAuthenticated,
  isAdmin,
  t,
}: {
  pathname: string
  isAuthenticated: boolean
  isAdmin: boolean
  t: TFunction
}): ShellNavItem[] {
  const items: ShellNavItem[] = [
    {
      key: "community",
      to: "/",
      label: translate(t, "community.nav.community", "Community"),
      icon: Compass,
      active: isCommunityRoute(pathname),
    },
    {
      key: "tools",
      to: "/tools",
      label: translate(t, "community.nav.paperTool", "Paper Tool"),
      icon: PenTool,
      active: isPaperToolRoute(pathname),
    },
  ]

  if (isAuthenticated) {
    items.splice(1, 0, {
      key: "favorites",
      to: "/favorites",
      label: translate(t, "community.nav.favorites", "Favorites"),
      icon: Bookmark,
      active: isFavoritesRoute(pathname),
    })
  }

  if (isAdmin) {
    items.push({
      key: "agent",
      to: "/agent",
      label: translate(t, "community.conversation.title", "Paper Copilot"),
      icon: Sparkles,
      active: isPaperCopilotRoute(pathname),
    })
  }

  return items
}

export function getMobilePrimaryNavItems({
  pathname,
  t,
}: {
  pathname: string
  t: TFunction
}): ShellNavItem[] {
  return [
    {
      key: "community",
      to: "/",
      label: translate(t, "community.nav.community", "Community"),
      icon: Compass,
      active: isCommunityRoute(pathname),
    },
    {
      key: "favorites",
      to: "/favorites",
      label: translate(t, "community.nav.favorites", "Favorites"),
      icon: Bookmark,
      active: isFavoritesRoute(pathname),
    },
    {
      key: "tools",
      to: "/tools",
      label: translate(t, "community.nav.paperTool", "Paper Tool"),
      icon: PenTool,
      active: isPaperToolRoute(pathname),
    },
    {
      key: "profile",
      to: "/profile",
      label: translate(t, "profile.settings_and_account", "Settings & account"),
      imageAlt: translate(t, "profile.settings_and_account", "Settings & account"),
      active: isProfileRoute(pathname),
    },
  ]
}

export function renderShellNavItemIcon(item: ShellNavItem, className: string) {
  if (item.imageAlt) {
    return <MobileAccountNavIcon className={className} alt={item.imageAlt} />
  }

  const Icon = item.icon
  return Icon ? <Icon className={className} /> : null
}

export function getMobileShellTitle(pathname: string, t: TFunction) {
  if (pathname === "/" || pathname.startsWith("/paper/")) {
    return translate(t, "community.nav.community", "Community")
  }
  if (pathname.startsWith("/tools")) {
    return translate(t, "community.nav.paperTool", "Paper Tool")
  }
  if (pathname.startsWith("/favorites")) {
    return translate(t, "community.nav.favorites", "Favorites")
  }
  if (pathname.startsWith("/translate")) {
    return translate(t, "community.actions.translate", "Translate")
  }
  if (pathname.startsWith("/processing")) {
    return translate(t, "task.result.inProgress", "Processing")
  }
  if (pathname.startsWith("/preview")) {
    return translate(t, "comparison.title", "Preview")
  }
  if (pathname.startsWith("/workspace/history")) {
    return translate(t, "history.history", "History")
  }
  if (pathname.startsWith("/workspace/settings")) {
    return translate(t, "settings.title", "Settings")
  }
  if (pathname.startsWith("/workspace/glossary")) {
    return translate(t, "glossary.glossary_management", "Glossary")
  }
  if (pathname.startsWith("/admin/curation/tasks")) {
    return translate(t, "community.admin.nav.tasks", "Admin tasks")
  }
  if (pathname.startsWith("/admin/curation")) {
    return translate(t, "community.admin.nav.curation", "Admin curation")
  }
  if (pathname.startsWith("/agent")) {
    return translate(t, "community.conversation.title", "Paper Copilot")
  }
  if (pathname.startsWith("/profile")) {
    return translate(t, "profile.profile", "Profile")
  }

  return translate(t, "brand.name", "PaperX")
}
