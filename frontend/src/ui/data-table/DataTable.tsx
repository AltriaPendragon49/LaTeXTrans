import type { HTMLAttributes } from "react"

import { cn } from "@/lib/utils"

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

export function DataTableCell({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("min-w-0", className)} {...props} />
}
