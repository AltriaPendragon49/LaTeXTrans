/**
 * 切换按钮组件 - 基于 Radix UI Toggle 封装
 * 渲染可按下/释放状态的切换按钮，支持多种尺寸和变体
 */
"use client"

import * as React from "react"
import * as TogglePrimitive from "@radix-ui/react-toggle"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/** 切换按钮样式变体配置 */
const toggleVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-full border border-transparent text-sm font-medium text-[color:var(--px-shell-muted)] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/20 disabled:pointer-events-none disabled:opacity-50 data-[state=on]:border-[color:var(--px-shell-accent)]/18 data-[state=on]:bg-[color:var(--px-shell-accent-soft)] data-[state=on]:text-[color:var(--px-shell-accent)] [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-transparent",
        outline:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-sm hover:border-[color:var(--px-shell-accent)]/24 hover:bg-[color:var(--px-shell-panel-strong)] hover:text-[color:var(--px-shell-ink)]",
      },
      size: {
        default: "h-9 px-2 min-w-9",
        sm: "h-8 px-1.5 min-w-8",
        lg: "h-10 px-2.5 min-w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

/** 切换按钮组件，支持 pressed/unpressed 状态，具备 active 高亮样式 */
const Toggle = React.forwardRef<
  React.ElementRef<typeof TogglePrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof TogglePrimitive.Root> &
    VariantProps<typeof toggleVariants>
>(({ className, variant, size, ...props }, ref) => (
  <TogglePrimitive.Root
    ref={ref}
    className={cn(toggleVariants({ variant, size, className }))}
    {...props}
  />
))

Toggle.displayName = TogglePrimitive.Root.displayName

export { Toggle, toggleVariants }
