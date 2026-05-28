/**
 * 搜索栏组件
 * 渲染带输入框和提交按钮的搜索表单，支持单行和多行模式，以及 inline/feature 两种样式
 */
import type { FormEvent, KeyboardEvent, ReactNode } from "react"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"
import { Button } from "@/ui/button/Button"
import { Input } from "@/ui/input/Input"
import { Textarea } from "@/ui/input/Textarea"

/** 搜索栏样式变体：inline（紧凑） / feature（突出展示） */
const searchBarVariants = cva(
  "border border-[color:var(--px-shell-line)] text-[color:var(--px-shell-ink)] shadow-[var(--px-shell-shadow)]",
  {
    variants: {
      variant: {
        inline:
          "rounded-md bg-[color:var(--px-shell-panel)] px-4 py-3",
        feature:
          "rounded-md bg-[linear-gradient(135deg,color-mix(in_srgb,var(--px-shell-panel-strong)_96%,white),color-mix(in_srgb,var(--px-shell-accent-soft)_18%,white))] px-4 py-4 md:px-5 md:py-5",
      },
    },
    defaultVariants: {
      variant: "inline",
    },
  },
)

/** SearchBar 组件 Props */
interface SearchBarProps extends VariantProps<typeof searchBarVariants> {
  /** 当前输入值 */
  value: string
  /** 值变更回调 */
  onValueChange: (value: string) => void
  /** 提交回调，传入当前值 */
  onSubmit: (value: string) => void
  /** 占位文本 */
  placeholder: string
  /** 无障碍标签 */
  ariaLabel: string
  /** 提交按钮标签 */
  actionLabel: string
  /** 提交按钮图标 */
  actionIcon?: ReactNode
  /** 辅助操作按钮 */
  auxiliaryAction?: ReactNode
  /** 元信息区域 */
  meta?: ReactNode
  /** 是否禁用 */
  disabled?: boolean
  /** 是否多行模式 */
  multiline?: boolean
  /** 额外样式 */
  className?: string
  /** 输入框额外样式 */
  inputClassName?: string
}

/** 搜索栏，multiline 使用 Textarea 组件，Enter 提交（Shift+Enter 换行） */
export function SearchBar({
  value,
  onValueChange,
  onSubmit,
  placeholder,
  ariaLabel,
  actionLabel,
  actionIcon,
  auxiliaryAction,
  meta,
  disabled = false,
  multiline = false,
  variant,
  className,
  inputClassName,
}: SearchBarProps) {
  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    onSubmit(value)
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (!multiline) {
      return
    }

    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      onSubmit(value)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(searchBarVariants({ variant }), className)}
    >
      <div className={cn("flex gap-3", variant === "feature" ? "items-start" : "items-center")}>
        <div className="min-w-0 flex-1 space-y-2.5">
          {multiline ? (
            <Textarea
              aria-label={ariaLabel}
              value={value}
              onChange={(event) => onValueChange(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled}
              className={cn("min-h-[108px] border-none bg-transparent px-0 py-0 shadow-none focus-visible:ring-0", inputClassName)}
            />
          ) : (
            <Input
              aria-label={ariaLabel}
              value={value}
              onChange={(event) => onValueChange(event.target.value)}
              placeholder={placeholder}
              disabled={disabled}
              className={cn("min-h-9 border-none bg-transparent px-0 py-0 text-[15px] shadow-none focus-visible:ring-0", inputClassName)}
            />
          )}

          <div className="flex flex-col gap-2 border-t border-[color:var(--px-shell-line)]/75 pt-2.5 md:flex-row md:items-center md:justify-between">
            {meta ? (
              <div className="min-w-0">{meta}</div>
            ) : (
              <div />
            )}

            <div className="flex flex-wrap items-center justify-end gap-2">
              {auxiliaryAction}
              <Button
                type="submit"
                disabled={disabled}
                className={cn(variant === "feature" ? "px-7" : "px-5")}
              >
                {actionIcon}
                {actionLabel}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </form>
  )
}
