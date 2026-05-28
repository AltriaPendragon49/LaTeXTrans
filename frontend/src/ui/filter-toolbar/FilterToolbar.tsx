/**
 * 筛选工具栏组件
 * 渲染一组可切换的筛选按钮，用于在不同选项间切换数据视图
 */
import type { HTMLAttributes, ReactNode } from "react"

import { Button } from "@/ui/button/Button"
import { cn } from "@/lib/utils"

/** 单个筛选选项 */
interface FilterToolbarOption {
  /** 选项值 */
  value: string
  /** 选项标签 */
  label: ReactNode
  /** 可选的图标 */
  icon?: ReactNode
}

/** FilterToolbar 组件 Props */
interface FilterToolbarProps extends HTMLAttributes<HTMLDivElement> {
  /** 可选筛选选项列表 */
  options: FilterToolbarOption[]
  /** 当前选中的值 */
  value: string
  /** 值变更回调 */
  onValueChange: (value: string) => void
  /** 右侧元信息区域 */
  meta?: ReactNode
  /** 额外操作按钮 */
  actions?: ReactNode
}

/** 筛选工具栏，以药丸形按钮组切换视图，可选附加操作和元信息 */
export function FilterToolbar({
  options,
  value,
  onValueChange,
  meta,
  actions,
  className,
  ...props
}: FilterToolbarProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-3 border-b border-[color:var(--px-shell-line)] pb-3 lg:flex-row lg:items-center lg:justify-between",
        className,
      )}
      {...props}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
        <div className="inline-flex flex-wrap gap-2 rounded-full border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-1 shadow-[0_12px_28px_rgba(15,23,42,0.05)]">
          {options.map((option) => {
            const active = option.value === value

            return (
              <Button
                key={option.value}
                type="button"
                variant={active ? "secondary" : "ghost"}
                onClick={() => onValueChange(option.value)}
                className={cn(
                  "min-h-10 rounded-full px-4 py-2 text-sm",
                  active
                    ? "bg-[color:var(--px-shell-accent-soft)] text-[color:var(--px-shell-accent)] shadow-[inset_0_0_0_1px_rgba(18,118,199,0.16)]"
                    : "text-[color:var(--px-shell-muted)] hover:bg-[color:var(--px-shell-panel)] hover:text-[color:var(--px-shell-ink)]",
                )}
                aria-pressed={active}
              >
                {option.icon ? <span className="flex items-center">{option.icon}</span> : null}
                <span>{option.label}</span>
              </Button>
            )
          })}
        </div>

        {actions ? <div className="flex flex-wrap items-center gap-2">{actions}</div> : null}
      </div>

      {meta ? <div className="flex flex-wrap items-center gap-3">{meta}</div> : null}
    </div>
  )
}
