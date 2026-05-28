/**
 * 工具提示组件 - 基于 Radix UI Tooltip 封装
 * 在元素 hover 或 focus 时显示浮动的提示文本
 */
import * as React from "react"
import * as TooltipPrimitive from "@radix-ui/react-tooltip"

import { cn } from "@/lib/utils"

/** 工具提示 Provider，需包裹在应用根处以提供全局 Tooltip 上下文 */
const TooltipProvider = TooltipPrimitive.Provider

/** 工具提示根组件 */
const Tooltip = TooltipPrimitive.Root

/** 工具提示触发器，hover/focus 时触发提示显示 */
const TooltipTrigger = TooltipPrimitive.Trigger

/** 工具提示内容气泡，显示在触发器附近 */
const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Portal>
    <TooltipPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={cn(
        "z-50 overflow-hidden rounded-xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] px-3 py-1.5 text-xs text-[color:var(--px-shell-ink)] shadow-[0_18px_40px_rgba(15,23,42,0.16)] animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 origin-[--radix-tooltip-content-transform-origin]",
        className
      )}
      {...props}
    />
  </TooltipPrimitive.Portal>
))
TooltipContent.displayName = TooltipPrimitive.Content.displayName

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider }
