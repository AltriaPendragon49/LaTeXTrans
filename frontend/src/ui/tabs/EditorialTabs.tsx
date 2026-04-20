import * as React from "react"

import { cn } from "@/lib/utils"
import { Tabs, TabsList, TabsTrigger } from "@/ui/primitives/tabs"

type EditorialTabsProps = React.ComponentProps<typeof Tabs>
type EditorialTabsListProps = React.ComponentProps<typeof TabsList>
type EditorialTabsTriggerProps = React.ComponentProps<typeof TabsTrigger>

export function EditorialTabs(props: EditorialTabsProps) {
  return <Tabs {...props} />
}

export function EditorialTabsList({ className, ...props }: EditorialTabsListProps) {
  return (
    <TabsList
      className={cn(
        "h-auto rounded-[20px] border border-[color:var(--px-shell-line)] bg-white/72 p-1.5 shadow-sm",
        className,
      )}
      {...props}
    />
  )
}

export function EditorialTabsTrigger({ className, ...props }: EditorialTabsTriggerProps) {
  return (
    <TabsTrigger
      className={cn(
        "rounded-[14px] px-5 py-2.5 text-sm font-semibold text-[color:var(--px-shell-muted)] transition-all data-[state=active]:bg-[color:var(--px-shell-panel)] data-[state=active]:text-[color:var(--px-shell-ink)] data-[state=active]:shadow-[0_12px_28px_-20px_rgba(8,23,38,0.28)]",
        className,
      )}
      {...props}
    />
  )
}
