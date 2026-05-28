/**
 * 主题切换按钮组件
 * 渲染用于切换亮色/暗色主题的按钮，显示当前模式，并自适应图标
 */
import { MoonStar, SunMedium } from "lucide-react"
import { useTheme } from "next-themes"
import { useTranslation } from "react-i18next"

import { Button } from "@/ui/button/Button"

/** 主题切换按钮，在 light/dark 间切换，图标和文本跟随当前主题自适应 */
export function ThemeToggle() {
  const { t } = useTranslation()
  const { theme, setTheme } = useTheme()

  const currentTheme = theme === "light" ? "light" : "dark"
  const isDark = currentTheme === "dark"
  const nextTheme = isDark ? "light" : "dark"
  const actionLabel = isDark
    ? t("theme.toggle.switchToLight")
    : t("theme.toggle.switchToDark")
  const modeLabel = isDark ? t("theme.mode.dark") : t("theme.mode.light")

  return (
    <Button
      type="button"
      variant="ghost"
      size="sm"
      aria-label={actionLabel}
      title={actionLabel}
      onClick={() => setTheme(nextTheme)}
      className="h-11 min-w-11 rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-3 text-[color:var(--px-shell-ink)] transition-colors hover:bg-[color:var(--px-shell-panel)]"
    >
      {isDark ? (
        <MoonStar className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
      ) : (
        <SunMedium className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
      )}
      <span className="hidden text-sm sm:inline">{modeLabel}</span>
    </Button>
  )
}
