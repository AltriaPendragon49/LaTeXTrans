/**
 * 数据表格组件
 * 渲染结构化表格布局，包含表头、表体和行/单元格子组件
 */
import type { HTMLAttributes } from "react"

import { cn } from "@/lib/utils"

/** 数据表格根容器，带圆角、边框和阴影 */
export function DataTable({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-[24px] border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-[var(--px-shell-shadow)]",
        className,
      )}
      {...props}
    />
  )
}

/** 表格头区域容器，固定在表格顶部 */
export function DataTableHeader({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "border-b border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)]",
        className,
      )}
      {...props}
    />
  )
}

/** 表头行，使用 CSS Grid 布局 */
export function DataTableHeaderRow({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("grid gap-4 px-6 py-4", className)}
      {...props}
    />
  )
}

/** 表头单元格，大写加粗样式 */
export function DataTableHeaderCell({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "text-[10px] font-bold uppercase tracking-widest text-[color:var(--px-shell-muted)]",
        className,
      )}
      {...props}
    />
  )
}

/** 表格体容器，行之间用分隔线分隔 */
export function DataTableBody({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("divide-y divide-[color:var(--px-shell-line)]/60", className)}
      {...props}
    />
  )
}

/** 表格数据行，使用 CSS Grid 布局 */
export function DataTableRow({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("grid gap-4 px-4 py-4 sm:px-6 sm:py-4", className)}
      {...props}
    />
  )
}

/** 表格数据单元格 */
export function DataTableCell({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("min-w-0", className)} {...props} />
}
