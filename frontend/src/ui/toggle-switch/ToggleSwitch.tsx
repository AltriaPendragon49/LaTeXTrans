/**
 * 开关切换组件（纯 CSS 实现）
 * 基于 button[role=switch]，渲染可切换 on/off 的开关控件，不依赖 Radix
 */
import type { ButtonHTMLAttributes } from "react"

import { cn } from "@/lib/utils"

/** ToggleSwitch 组件 Props */
interface ToggleSwitchProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onChange"> {
  /** 当前开关状态 */
  checked: boolean
  /** 状态变更回调 */
  onCheckedChange: (checked: boolean) => void
}

/** 纯 CSS 开关控件，使用 button + role="switch" 实现，与 Radix Switch 视觉一致 */
export function ToggleSwitch({
  checked,
  onCheckedChange,
  className,
  disabled,
  ...props
}: ToggleSwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => {
        if (!disabled) {
          onCheckedChange(!checked)
        }
      }}
      className={cn(
        "relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border border-transparent transition-all duration-200",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/30 focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--px-shell-panel)]",
        "disabled:cursor-not-allowed disabled:opacity-50",
        checked
          ? "bg-[color:var(--px-shell-accent)] shadow-[0_0_0_4px_color-mix(in_srgb,var(--px-shell-accent)_16%,transparent)]"
          : "bg-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-line-strong)]",
        className,
      )}
      {...props}
    >
      <span
        className={cn(
          "pointer-events-none block h-5 w-5 rounded-full bg-white shadow-sm ring-1 ring-black/5 transition-transform duration-200",
          checked ? "translate-x-5" : "translate-x-0",
        )}
      />
    </button>
  )
}
