/**
 * 分区卡片组件
 * 基于 Card 封装，渲染带图标、标题、描述和头部操作的区块卡片
 */
import type { HTMLAttributes, ReactNode } from "react"

import { cn } from "@/lib/utils"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/ui/card/Card"

/** SectionCard 组件 Props */
interface SectionCardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  /** 可选图标 */
  icon?: ReactNode
  /** 区块标题 */
  title: ReactNode
  /** 可选描述 */
  description?: ReactNode
  /** 头部右侧操作区域 */
  headerAside?: ReactNode
  /** 头部额外样式 */
  headerClassName?: string
  /** 内容区额外样式 */
  contentClassName?: string
  /** 图标额外样式 */
  iconClassName?: string
}

/** 分区卡片，基于 Card 构建，提供 icon + title + description + headerAside 的标准布局 */
export function SectionCard({
  icon,
  title,
  description,
  headerAside,
  headerClassName,
  contentClassName,
  iconClassName,
  className,
  children,
  ...props
}: SectionCardProps) {
  return (
    <Card className={cn("overflow-hidden shadow-none", className)} {...props}>
      <CardHeader
        className={cn(
          "flex flex-row items-start justify-between gap-4 bg-white/48",
          headerClassName,
        )}
      >
        <div className="flex min-w-0 items-start gap-3">
          {icon ? (
            <div
              className={cn(
                "flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] text-[color:var(--px-shell-accent)]",
                iconClassName,
              )}
            >
              {icon}
            </div>
          ) : null}

          <div className="min-w-0 space-y-1">
            <CardTitle className="text-base font-bold tracking-tight">{title}</CardTitle>
            {description ? (
              <CardDescription className="text-xs leading-5">{description}</CardDescription>
            ) : null}
          </div>
        </div>

        {headerAside ? <div className="shrink-0">{headerAside}</div> : null}
      </CardHeader>

      <CardContent className={cn("px-6 py-5", contentClassName)}>
        {children}
      </CardContent>
    </Card>
  )
}
