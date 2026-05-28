/**
 * 标签页组件 - 基于 Radix UI Tabs 封装
 * 提供标签页切换界面，包含标签列表、触发器和内容面板
 */
import * as React from "react"
import * as TabsPrimitive from "@radix-ui/react-tabs"

import { cn } from "@/lib/utils"

/** 标签页根组件 */
const Tabs = TabsPrimitive.Root

/** 标签页列表容器，包裹所有标签触发器 */
const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn(
      "inline-flex h-auto items-center justify-center rounded-[18px] border border-[color:var(--px-shell-line)] bg-white/72 p-1.5 text-[color:var(--px-shell-muted)] shadow-sm",
      className
    )}
    {...props}
  />
))
TabsList.displayName = TabsPrimitive.List.displayName

/** 标签页触发器，点击切换到对应内容面板 */
const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "inline-flex items-center justify-center whitespace-nowrap rounded-[14px] px-4 py-2 text-sm font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent)]/20 focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--px-shell-panel)] disabled:pointer-events-none disabled:opacity-50 data-[state=active]:bg-[color:var(--px-shell-panel)] data-[state=active]:text-[color:var(--px-shell-ink)] data-[state=active]:shadow-[0_12px_28px_-20px_rgba(8,23,38,0.28)]",
      className
    )}
    {...props}
  />
))
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName

/** 标签页内容面板，与对应标签触发器关联显示 */
const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn(
      "mt-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color:var(--px-shell-accent-soft)] focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--px-shell-panel)]",
      className
    )}
    {...props}
  />
))
TabsContent.displayName = TabsPrimitive.Content.displayName

export { Tabs, TabsList, TabsTrigger, TabsContent }
