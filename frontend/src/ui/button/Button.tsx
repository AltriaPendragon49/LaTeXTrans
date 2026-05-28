/**
 * 按钮组件 - 基于 class-variance-authority 和 Radix Slot 构建
 * 支持多种样式变体和尺寸，可使用 asChild 委托给子元素
 */
import * as React from "react"
import { Slot } from "@radix-ui/react-slot"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/** 按钮样式变体配置：default / outline / secondary / ghost / ink / destructive / action */
const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full border text-sm font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/20 disabled:pointer-events-none disabled:opacity-55 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "border-[color:var(--px-shell-accent)] bg-[color:var(--px-shell-accent)] text-white shadow-[var(--px-shell-shadow)] hover:-translate-y-0.5 hover:border-[color:var(--px-shell-accent-strong)] hover:bg-[color:var(--px-shell-accent-strong)]",
        outline:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)] hover:-translate-y-0.5 hover:border-[color:var(--px-shell-accent)]/30 hover:text-[color:var(--px-shell-accent)]",
        secondary:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)] hover:-translate-y-0.5 hover:bg-[color:var(--px-shell-panel)]",
        ghost:
          "border-transparent bg-transparent text-[color:var(--px-shell-muted)] hover:border-[color:var(--px-shell-line)] hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]",
        ink:
          "border-[color:var(--px-shell-ink)] bg-[color:var(--px-shell-ink)] text-[color:var(--px-shell-surface)] hover:-translate-y-0.5 hover:opacity-95",
        destructive:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-strong)] text-[color:var(--px-shell-danger-contrast)] hover:-translate-y-0.5 hover:bg-[color:var(--px-shell-danger)]",
        action:
          "border-[color:color-mix(in_srgb,var(--px-shell-accent)_72%,white)] bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-accent)_60%,white),var(--px-shell-accent))] text-white shadow-[0_14px_28px_-18px_rgba(35,169,255,0.55)] hover:-translate-y-0.5 hover:border-[color:var(--px-shell-accent-strong)] hover:bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-accent)_42%,white),var(--px-shell-accent-strong))] hover:text-white hover:shadow-[0_18px_36px_-20px_rgba(35,169,255,0.62)]",
      },
      size: {
        default: "min-h-11 px-5 py-2.5",
        sm: "min-h-9 px-4 py-2 text-xs uppercase tracking-[0.16em]",
        lg: "min-h-12 px-6 py-3",
        chip: "min-h-9 px-3.5 py-2 text-[11px] uppercase tracking-[0.14em]",
        icon: "h-10 w-10 rounded-full p-0",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

/** 按钮组件 Props，支持 asChild 委托渲染 */
export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

/** 按钮组件，支持 7 种 Variant 和 5 种 Size，通过 asChild 可渲染为任意元素 */
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button"

    return (
      <Comp
        ref={ref}
        className={cn(buttonVariants({ variant, size }), className)}
        {...props}
      />
    )
  },
)

Button.displayName = "Button"

export { Button, buttonVariants }
