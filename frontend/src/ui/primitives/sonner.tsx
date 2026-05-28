/**
 * Toast 通知组件 - 基于 Sonner 封装
 * 渲染全局 Toast 通知容器，自动跟随主题切换
 */
import { useTheme } from "next-themes"
import { Toaster as Sonner } from "sonner"

type ToasterProps = React.ComponentProps<typeof Sonner>

/** Toast 通知容器，集成主题系统，统一管理全局通知样式 */
const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast:
            "group toast group-[.toaster]:border-[color:var(--px-shell-line)] group-[.toaster]:bg-[color:var(--px-shell-panel)] group-[.toaster]:text-[color:var(--px-shell-ink)] group-[.toaster]:shadow-[var(--px-shell-shadow)]",
          description: "group-[.toast]:text-[color:var(--px-shell-muted)]",
          actionButton:
            "group-[.toast]:border-[color:var(--px-shell-accent)] group-[.toast]:bg-[color:var(--px-shell-accent)] group-[.toast]:text-white",
          cancelButton:
            "group-[.toast]:border-[color:var(--px-shell-line)] group-[.toast]:bg-[color:var(--px-shell-panel-strong)] group-[.toast]:text-[color:var(--px-shell-muted)]",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
