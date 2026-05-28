/**
 * 面板外壳组件
 * 渲染通用的面板容器，支持多种视觉风格（panel / glass / hero / accent / success / warning / danger）
 */
import { createElement, type HTMLAttributes } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/** 面板外壳样式变体 */
const panelShellVariants = cva(
  "border text-[color:var(--px-shell-ink)]",
  {
    variants: {
      tone: {
        panel:
          "rounded-[28px] border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-[var(--px-shell-shadow)]",
        glass:
          "rounded-[30px] border-[color:var(--px-shell-line)] bg-[color:color-mix(in_srgb,var(--px-shell-panel)_92%,white)] shadow-[0_22px_55px_rgba(15,23,42,0.08)] backdrop-blur-sm",
        hero:
          "rounded-[28px] border-[color:var(--px-shell-line)] bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-panel)_92%,white),color-mix(in_srgb,var(--px-shell-panel-strong)_86%,var(--px-shell-surface)))] shadow-[0_18px_45px_rgba(15,23,42,0.06)]",
        accent:
          "rounded-[28px] border-[color:var(--px-shell-accent)]/18 bg-[color:var(--px-shell-accent-soft)] shadow-[0_18px_45px_rgba(15,23,42,0.06)]",
        success:
          "rounded-[28px] border-[color:var(--px-shell-success-line)] bg-[color:var(--px-shell-success-soft)] shadow-[0_18px_45px_rgba(15,23,42,0.06)]",
        warning:
          "rounded-[28px] border-[color:var(--px-shell-warning-line)] bg-[color:var(--px-shell-warning-soft)] shadow-[0_18px_45px_rgba(15,23,42,0.06)]",
        danger:
          "rounded-[28px] border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] shadow-[0_18px_45px_rgba(15,23,42,0.06)]",
      },
      padding: {
        none: "",
        default: "px-5 py-5",
        compact: "px-4 py-4",
      },
    },
    defaultVariants: {
      tone: "panel",
      padding: "default",
    },
  },
)

/** PanelShell 组件 Props */
interface PanelShellProps
  extends HTMLAttributes<HTMLElement>,
    VariantProps<typeof panelShellVariants> {
  /** 渲染的 HTML 标签名，可选 div / section / aside */
  as?: "div" | "section" | "aside"
}

/** 通用面板外壳，通过 as 属性自由切换渲染标签 */
export function PanelShell({
  as = "div",
  tone,
  padding,
  className,
  ...props
}: PanelShellProps) {
  return createElement(as, {
    className: cn(panelShellVariants({ tone, padding }), className),
    ...props,
  })
}
