/**
 * 可展开卡片组件（Disclosure Card）
 * 基于 Collapsible 封装，渲染可点击展开/折叠的内容卡片，头部显示标题和展开箭头
 */
import type { HTMLAttributes, ReactNode } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"

import { cn } from "@/lib/utils"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/ui/primitives/collapsible"

/** DisclosureCard 组件 Props */
interface DisclosureCardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  /** 是否展开 */
  open: boolean
  /** 展开/折叠状态变更回调 */
  onOpenChange: (open: boolean) => void
  /** 卡片标题 */
  title: ReactNode
  /** 标题上方小字 */
  eyebrow?: ReactNode
  /** 可选描述 */
  description?: ReactNode
  /** 头部右侧附加内容 */
  headerAside?: ReactNode
  /** 内容区域额外样式 */
  contentClassName?: string
}

/** 可展开卡片，点击头部切换折叠。展开时显示 ChevronUp，折叠时显示 ChevronDown */
export function DisclosureCard({
  open,
  onOpenChange,
  title,
  eyebrow,
  description,
  headerAside,
  contentClassName,
  className,
  children,
  ...props
}: DisclosureCardProps) {
  return (
    <Collapsible open={open} onOpenChange={onOpenChange}>
      <div
        className={cn(
          "overflow-hidden rounded-none border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel)] shadow-none",
          className,
        )}
        {...props}
      >
        <CollapsibleTrigger asChild>
          <button
            type="button"
            className="flex w-full items-start justify-between gap-3 px-4 py-4 text-left transition-colors hover:bg-[color:var(--px-shell-panel-strong)]"
          >
            <div className="min-w-0 flex-1 space-y-1.5">
              {eyebrow ? (
                <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[color:var(--px-shell-muted)]">
                  {eyebrow}
                </div>
              ) : null}
              <div className="text-sm font-semibold text-[color:var(--px-shell-ink)]">{title}</div>
              {description ? (
                <div className="text-xs leading-6 text-[color:var(--px-shell-muted)]">{description}</div>
              ) : null}
            </div>

            <div className="flex shrink-0 items-center gap-3 pl-2">
              {headerAside ? <div className="shrink-0">{headerAside}</div> : null}
              {open ? (
                <ChevronUp className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
              ) : (
                <ChevronDown className="h-4 w-4 text-[color:var(--px-shell-muted)]" />
              )}
            </div>
          </button>
        </CollapsibleTrigger>

        <CollapsibleContent className="border-t border-[color:var(--px-shell-line)]">
          <div className={cn("px-4 py-4 text-sm text-[color:var(--px-shell-muted)]", contentClassName)}>
            {children}
          </div>
        </CollapsibleContent>
      </div>
    </Collapsible>
  )
}
