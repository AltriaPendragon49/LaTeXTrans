/**
 * 折叠面板组件 - 基于 Radix UI Collapsible 封装
 * 提供可展开/折叠的内容区域
 */
"use client"

import * as CollapsiblePrimitive from "@radix-ui/react-collapsible"

/** 折叠面板根组件 */
const Collapsible = CollapsiblePrimitive.Root

/** 折叠面板触发器，点击可切换展开/折叠状态 */
const CollapsibleTrigger = CollapsiblePrimitive.CollapsibleTrigger

/** 折叠面板内容区域，展开时显示，折叠时隐藏 */
const CollapsibleContent = CollapsiblePrimitive.CollapsibleContent

export { Collapsible, CollapsibleTrigger, CollapsibleContent }
