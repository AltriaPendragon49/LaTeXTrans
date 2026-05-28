/**
 * 卡片组件
 * 渲染带标题、描述、内容和底部的卡片容器，支持多种面板风格
 */
import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

/** 卡片样式变体配置：panel / strong / soft / ink / danger */
const cardVariants = cva(
  "rounded-[28px] border shadow-[var(--px-shell-shadow)]",
  {
    variants: {
      variant: {
        panel: "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)]",
        strong:
          "border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-ink)]",
        soft: "border-[color:var(--px-shell-line)] bg-white/78 text-[color:var(--px-shell-ink)]",
        ink: "border-[color:var(--px-shell-ink)] bg-[color:var(--px-shell-ink)] text-[color:var(--px-shell-surface)]",
        danger:
          "border-[color:var(--px-shell-danger-line)] bg-[color:var(--px-shell-danger-soft)] text-[color:var(--px-shell-danger)] shadow-none",
      },
      padding: {
        default: "",
        compact: "",
      },
    },
    defaultVariants: {
      variant: "panel",
      padding: "default",
    },
  },
)

type CardProps = React.HTMLAttributes<HTMLDivElement> &
  VariantProps<typeof cardVariants>

/** 卡片根容器 */
const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant, padding, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(cardVariants({ variant, padding }), className)}
      {...props}
    />
  ),
)

Card.displayName = "Card"

/** 卡片头部区域（标题 + 描述），带底部分隔线 */
const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col gap-2 border-b border-[color:var(--px-shell-line)] px-6 py-5", className)}
    {...props}
  />
))

CardHeader.displayName = "CardHeader"

/** 卡片标题 */
const CardTitle = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-lg font-black leading-tight tracking-[-0.02em]", className)}
    {...props}
  />
))

CardTitle.displayName = "CardTitle"

/** 卡片描述文本 */
const CardDescription = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm leading-6 text-[color:var(--px-shell-muted)]", className)}
    {...props}
  />
))

CardDescription.displayName = "CardDescription"

/** 卡片内容区域 */
const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("px-6 py-5", className)} {...props} />
))

CardContent.displayName = "CardContent"

/** 卡片底部操作区域，带顶部分隔线 */
const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center gap-3 border-t border-[color:var(--px-shell-line)] px-6 py-5", className)}
    {...props}
  />
))

CardFooter.displayName = "CardFooter"

export { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle }
