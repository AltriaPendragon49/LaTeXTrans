/**
 * 分段控制器组件
 * 渲染一组互斥的切换按钮，选中项有卡片高亮效果（类似 iOS SegmentedControl）
 */
import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

/** 分段控制器中的单个选项 */
interface SegmentedControlItem<T extends string> {
  /** 选项值 */
  value: T
  /** 选项标签 */
  label: ReactNode
  /** 可选图标 */
  icon?: ReactNode
  /** 是否禁用 */
  disabled?: boolean
  /** 测试 ID */
  testId?: string
}

/** SegmentedControl 组件 Props */
interface SegmentedControlProps<T extends string> {
  /** 当前选中值 */
  value: T
  /** 选项列表 */
  items: SegmentedControlItem<T>[]
  /** 值变更回调 */
  onValueChange: (value: T) => void
  /** 额外样式 */
  className?: string
  /** 选项按钮额外样式 */
  itemClassName?: string
}

/** 分段控制器，等分宽度，选中项浮起高亮，类似 iOS 风格 */
export function SegmentedControl<T extends string>({
  value,
  items,
  onValueChange,
  className,
  itemClassName,
}: SegmentedControlProps<T>) {
  return (
    <div
      className={cn(
        "flex w-full items-center gap-1 rounded-md border border-[color:var(--px-shell-line)] bg-[color:var(--px-shell-panel-strong)] p-1 shadow-inner",
        className,
      )}
    >
      {items.map((item) => {
        const active = item.value === value

        return (
          <button
            key={item.value}
            type="button"
            data-testid={item.testId}
            disabled={item.disabled}
            onClick={() => onValueChange(item.value)}
            className={cn(
              "flex-1 inline-flex min-h-9 items-center justify-center gap-1.5 rounded-sm px-4 py-2 text-xs font-bold uppercase tracking-[0.16em] transition-all duration-200",
              active
                ? "bg-[color:var(--px-shell-panel)] text-[color:var(--px-shell-ink)] shadow-sm border border-[color:var(--px-shell-line)]"
                : "text-[color:var(--px-shell-muted)] hover:text-[color:var(--px-shell-ink)] disabled:cursor-not-allowed disabled:opacity-45 border border-transparent",
              itemClassName,
            )}
          >
            {item.icon ? <span className="flex h-4 w-4 items-center justify-center">{item.icon}</span> : null}
            <span>{item.label}</span>
          </button>
        )
      })}
    </div>
  )
}
